#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "google-genai>=2.25",
#     "httpx>=0.28",
#     "openai>=3",
#     "python-dotenv",
#     "trafilatura>=2.0",
# ]
# ///

import argparse
import base64
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import httpx
import tomllib
import trafilatura
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

MESSAGES_JSON_NAME = "messages.json"
MESSAGES_TEXT_NAME = "messages.txt"
WEEK_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMAND_WEEKLY = "weekly"
COMMAND_TTS_SCRIPT = "tts-script"


def load_messages(filepath: str | Path) -> List[Dict[str, Any]]:
    "Load and filter messages from JSON file."
    with open(filepath, encoding="utf-8") as f:
        return [m for m in json.load(f) if m.get("time") and m.get("text") and m.get("author")]


def group_by_week(messages: List[Dict[str, Any]]) -> Dict[datetime.date, List[Dict[str, Any]]]:
    "Group messages by ISO-week (Sunday to Saturday, UTC)."
    groups = defaultdict(list)
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for message in messages:
        dt = datetime.datetime.fromisoformat(message["time"].replace("Z", "+00:00"))
        days_until_sunday = 7 - (dt.isoweekday() % 7)
        week_end = dt.date() + datetime.timedelta(days=days_until_sunday)
        if week_end > today:
            continue
        message["dt"] = dt
        groups[week_end].append(message)
    return groups


def with_message_datetimes(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    "Attach parsed UTC datetimes to already-filtered message rows."
    return [
        {
            **message,
            "dt": datetime.datetime.fromisoformat(message["time"].replace("Z", "+00:00")),
        }
        for message in messages
    ]


def serialize_week_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    "Serialize weekly messages for `$WEEK/messages.json`, dropping internal helper fields."
    return [
        {key: value for key, value in message.items() if key != "dt"}
        for message in sorted(items, key=lambda message: message["dt"])
    ]


def load_grouped_messages(script_dir: Path) -> Dict[datetime.date, List[Dict[str, Any]]]:
    """
    Load grouped weekly messages from `$WEEK/messages.json` when available.

    This lets `podcast.py` operate directly on the same per-week input structure written
    by `split_whatsapp_messages.py`. If no such files exist yet, it falls back to
    regrouping `gen-ai-messages.json`.
    """

    week_groups: Dict[datetime.date, List[Dict[str, Any]]] = {}
    for child in sorted(script_dir.iterdir()):
        if not child.is_dir() or not WEEK_DIR_PATTERN.match(child.name):
            continue
        messages_json = child / MESSAGES_JSON_NAME
        if not messages_json.exists():
            continue
        week_groups[datetime.date.fromisoformat(child.name)] = with_message_datetimes(
            load_messages(messages_json)
        )

    if week_groups:
        return week_groups

    return group_by_week(load_messages(script_dir / "gen-ai-messages.json"))


def build_threads(
    items: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    "Build message threads from items."
    by_id = {message["messageId"]: message for message in items}
    replies = defaultdict(list)
    for message in items:
        pid = message.get("quoteMessageId")
        if pid in by_id:
            replies[pid].append(message)
    roots = [message for message in items if message.get("quoteMessageId") not in by_id]
    roots.sort(key=lambda message: message["dt"])
    return replies, roots


def render_message(
    message: Dict[str, Any], replies_dict: Dict[str, List[Dict[str, Any]]], file, lvl: int = 0
) -> None:
    "Render a message and its replies to a file."
    indent = "  " * lvl
    line = f"{indent}- {message['author']}: {message['text'].replace(chr(10), ' ')}"
    if message.get("reactions"):
        line += f" [{message['reactions']}]"
    file.write(line + "\n")
    for reply in sorted(replies_dict[message["messageId"]], key=lambda item: item["dt"]):
        render_message(reply, replies_dict, file, lvl + 1)


def write_messages_json_file(week: datetime.date, items: List[Dict[str, Any]], target_dir: Path) -> Path:
    "Write the weekly JSON shard to `$WEEK/messages.json` if it doesn't exist yet."
    target_dir.mkdir(exist_ok=True)
    messages_json_file = target_dir / MESSAGES_JSON_NAME

    if messages_json_file.exists():
        return messages_json_file

    messages_json_file.write_text(
        json.dumps(serialize_week_items(items), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return messages_json_file


def write_messages_file(week: datetime.date, items: List[Dict[str, Any]], target_dir: Path) -> Path:
    "Write messages to a file in the target directory."
    target_dir.mkdir(exist_ok=True)
    messages_file = target_dir / MESSAGES_TEXT_NAME

    if messages_file.exists():
        return messages_file

    replies, roots = build_threads(items)
    with open(messages_file, "w", encoding="utf-8") as f:
        for root in roots:
            render_message(root, replies, f)
    return messages_file


DIALOGUE_FORMAT = {
    "type": "json_schema",
    "name": "podcast_dialogue",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "turns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {"type": "string", "enum": ["Alex", "Maya"]},
                        "text": {"type": "string"},
                        "style": {"type": "string"},
                        "new_section": {"type": "boolean"},
                    },
                    "required": ["speaker", "text", "style", "new_section"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["turns"],
        "additionalProperties": False,
    },
}
AUDIO_MIME = "audio/l16"
LEGACY_EVENTS = {"[laughs]": "<laugh>", "[short pause]": "<short pause>", "[sighs]": "<sigh>"}
LEGACY_STYLES = {"excited": "excited", "whispers": "whispering"}


def api_key(env: str, _llm_key: str) -> str:
    """Return a required API key loaded from the environment or .env."""
    if value := os.getenv(env):
        return value
    raise ValueError(f"{env} is not set")


def podcast_cache_dir():
    """Return the restartable cache directory for podcast model calls."""
    return Path.home() / ".cache" / "generative-ai-group-podcast"


def digest(*parts: str) -> str:
    "Return a short stable content hash for restartable model-call caches."
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:20]


def render_script_prompt(config: Dict[str, Any], week: datetime.date, target_words: int) -> str:
    "Render the podcast prompt for one week."
    return (
        config["podcast"]
        .replace("$WEEK", week.strftime("%d %B %Y"))
        .replace("$TARGET_WORDS", f"{target_words:,}")
    )


def load_previous_scripts(script_dir: Path, week: datetime.date) -> str:
    """Load the podcast scripts from the two immediately preceding weeks, when present."""
    scripts = []
    for weeks_ago in (2, 1):
        prior_week = week - datetime.timedelta(weeks=weeks_ago)
        path = script_dir / str(prior_week) / f"podcast-{prior_week}.md"
        if path.exists():
            scripts.append(f"## {path.name}\n{path.read_text(encoding='utf-8').strip()}")
    return "\n\n".join(scripts)


def fetch_link_contents(messages_text: str, config: Dict[str, Any]) -> str:
    """Fetch and extract linked pages directly; failures never block podcast generation."""
    settings = config.get("links", {})
    if settings.get("enabled", True) is False:
        return ""

    urls = []
    for raw_url in re.findall(r"https?://\S+", messages_text):
        url = raw_url.rstrip(").,]}>")
        if url not in urls:
            urls.append(url)

    max_urls = int(settings.get("max_urls", 10))
    max_chars = int(settings.get("max_chars", 3_000))
    timeout = float(settings.get("timeout", 20))
    cache_dir = podcast_cache_dir() / "links"
    cache_dir.mkdir(parents=True, exist_ok=True)
    sections = []

    for url in urls[:max_urls]:
        path = cache_dir / f"{digest(url)}.md"
        if path.exists():
            markdown = path.read_text(encoding="utf-8")
        else:
            try:
                response = httpx.get(
                    url,
                    follow_redirects=True,
                    timeout=timeout,
                    headers={"User-Agent": "Mozilla/5.0 podcast-context-fetcher"},
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                print(f"Skipping linked page {url}: {exc}", file=sys.stderr)
                continue

            markdown = (
                trafilatura.extract(
                    response.text,
                    output_format="markdown",
                    include_links=True,
                    include_images=False,
                )
                or ""
            ).strip()
            if not markdown:
                continue
            path.write_text(markdown, encoding="utf-8")

        sections.append(f"## {url}\n{markdown[:max_chars]}")

    return "\n\n".join(sections)


def format_dialogue(turns: Sequence[Dict[str, str]]) -> str:
    "Serialize structured dialogue to the human-readable podcast Markdown file."
    lines = []
    for turn in turns:
        if turn.get("new_section") and lines:
            lines.append("")
        style = f"[style: {turn['style'].strip()}] " if turn["style"].strip() else ""
        lines.append(f"{turn['speaker']}: {style}{turn['text'].strip()}")
    return "\n".join(lines) + "\n"


def parse_dialogue(script: str, speakers: Sequence[str]) -> List[Dict[str, str]]:
    "Parse generated or historical speaker-labelled scripts into structured turns."
    if not script.strip():
        raise ValueError("script is empty")

    speaker_re = re.compile(
        rf"^(?P<speaker>{'|'.join(re.escape(name) for name in speakers)}):\s*(?P<text>.*)$"
    )
    turns: List[Dict[str, str]] = []
    for line_no, raw_line in enumerate(script.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        match = speaker_re.match(line)
        if not match:
            if not turns:
                raise ValueError(f"line {line_no} must begin with one of: {', '.join(speakers)}")
            turns[-1]["text"] += " " + line
            continue

        text = match.group("text").strip()
        for old, new in LEGACY_EVENTS.items():
            text = text.replace(old, new)

        style = ""
        style_match = re.match(r"^\[style:\s*(.+?)\]\s*(.*)$", text)
        if style_match:
            style, text = style_match.groups()
        else:
            legacy_match = re.match(r"^\[([^\]]+)\]\s*(.*)$", text)
            if legacy_match and legacy_match.group(1).lower() in LEGACY_STYLES:
                style = LEGACY_STYLES[legacy_match.group(1).lower()]
                text = legacy_match.group(2)

        if not text:
            raise ValueError(f"speaker {match.group('speaker')} has an empty turn")
        turns.append({"speaker": match.group("speaker"), "text": text, "style": style})
    return turns


def get_podcast_script(
    messages_text: str,
    config: Dict[str, Any],
    week: datetime.date,
    previous_scripts: str = "",
) -> str:
    """Generate a structured podcast using the transcript, linked pages, and continuity context."""
    target_words = max(1_200, min(3_300, round(len(messages_text.split()) * 0.48)))
    prompt = render_script_prompt(config, week, target_words)

    user_content = f"CURRENT WEEK TRANSCRIPT — PRIMARY SOURCE\n\n{messages_text}"
    if link_content := fetch_link_contents(messages_text, config):
        user_content += (
            "\n\nLINKED PAGE CONTENT — CONTEXT ONLY\n\n"
            "Use this only to understand links discussed in the transcript. "
            "The current-week transcript remains the primary source.\n\n"
            f"{link_content}"
        )
    if previous_scripts:
        user_content += (
            "\n\nPREVIOUS EPISODES — CONTEXT ONLY\n\n"
            "Use these only for reference and continuity. Do not repeat or recap their topics, "
            "examples, takeaways, or phrasing. If the current-week transcript independently "
            "revisits a topic, briefly orient the listener and focus on what is new this week.\n\n"
            f"{previous_scripts}"
        )

    model = config.get("openai", {}).get("model", "gpt-6-luna")
    cache = podcast_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (
        "dialogue-"
        + digest(model, prompt, user_content, json.dumps(DIALOGUE_FORMAT, sort_keys=True))
        + ".json"
    )

    if path.exists():
        turns = json.loads(path.read_text(encoding="utf-8"))["turns"]
    else:
        print(f"Generating dialogue with {model}...", flush=True)
        response = OpenAI(api_key=api_key("OPENAI_API_KEY", "openai")).responses.create(
            model=model,
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_content},
            ],
            text={"format": DIALOGUE_FORMAT},
        )
        result = json.loads(response.output_text)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        turns = result["turns"]
    return format_dialogue(turns)


def speaker_voices(config: Dict[str, Any]) -> Dict[str, str]:
    "Return configured Gemini voice names keyed by podcast speaker."
    voices = {
        item["name"]: item["voice_name"] for item in config.get("gemini", {}).get("speakers", [])
    }
    if not voices:
        raise ValueError("config.toml must define [[gemini.speakers]] entries")
    return voices


def build_speech_content(turns: Sequence[Dict[str, str]]) -> List[Dict[str, Any]]:
    "Build Gemini Interactions content, adding style only when explicitly useful."
    content = []
    for turn in turns:
        metadata: Dict[str, str] = {"type": "speech_metadata", "speaker": turn["speaker"]}
        if turn["style"].strip():
            metadata["style"] = turn["style"].strip()
        content.append({"type": "text", "text": turn["text"], "annotations": [metadata]})
    return content


def audio_plan(script: str, config: Dict[str, Any]) -> Dict[str, Any]:
    "Validate a script and return the configured TTS execution plan."
    gemini = config["gemini"]
    voices = speaker_voices(config)
    turns = parse_dialogue(script, list(voices))
    chunk_size = int(gemini.get("chunk_size", 10))
    if chunk_size < 1:
        raise ValueError("gemini.chunk_size must be >= 1")
    return {
        "model": gemini.get("model", "gemini-3.8-flash-lite-tts"),
        "sample_rate": int(gemini.get("sample_rate", 24_000)),
        "chunk_size": chunk_size,
        "turn_count": len(turns),
        "chunk_count": (len(turns) + chunk_size - 1) // chunk_size,
        "speaker_names": list(dict.fromkeys(turn["speaker"] for turn in turns)),
        "voices": voices,
        "turns": turns,
    }


def synthesize_chunk(client: genai.Client, turns: Sequence[Dict[str, str]], plan: Dict[str, Any]) -> bytes:
    "Synthesize one multi-turn dialogue chunk as raw 16-bit PCM."
    interaction = client.interactions.create(
        model=plan["model"],
        input=[{"type": "user_input", "content": build_speech_content(turns)}],
        response_format={
            "type": "audio",
            "mime_type": AUDIO_MIME,
            "sample_rate": plan["sample_rate"],
        },
        generation_config={
            "speech_config": {
                "mode": "conversational",
                "speakers": [
                    {"speaker": speaker, "voice": voice}
                    for speaker, voice in plan["voices"].items()
                ],
            }
        },
    )
    return base64.b64decode(interaction.output_audio.data)


def generate_audio_from_script(
    script: str,
    output_path: Path,
    config: Dict[str, Any],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    "Generate podcast audio in restartable multi-turn chunks, then encode MP3 once."
    plan = audio_plan(script, config)
    result = {
        "command": COMMAND_TTS_SCRIPT,
        "audio_path": str(output_path.resolve()),
        **{key: plan[key] for key in ("model", "turn_count", "chunk_count", "speaker_names")},
    }
    if dry_run:
        return {**result, "status": "dry-run"}

    cache = podcast_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    client = None
    pcm_paths = []
    turns = plan["turns"]
    for index, offset in enumerate(range(0, len(turns), plan["chunk_size"]), 1):
        chunk = turns[offset : offset + plan["chunk_size"]]
        chunk_json = json.dumps(chunk, sort_keys=True)
        path = cache / (
            "audio-"
            + digest(
                plan["model"],
                json.dumps(plan["voices"], sort_keys=True),
                AUDIO_MIME,
                str(plan["sample_rate"]),
                chunk_json,
            )
            + ".pcm"
        )
        if not path.exists():
            print(f"Synthesizing chunk {index}/{plan['chunk_count']} with {plan['model']}...", flush=True)
            client = client or genai.Client(api_key=api_key("GEMINI_API_KEY", "gemini"))
            path.write_bytes(synthesize_chunk(client, chunk, plan))
        pcm_paths.append(path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".pcm") as pcm:
        for path in pcm_paths:
            pcm.write(path.read_bytes())
        pcm.flush()
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "s16le",
                "-ar",
                str(plan["sample_rate"]),
                "-ac",
                "1",
                "-i",
                pcm.name,
                "-c:a",
                "libmp3lame",
                "-q:a",
                "4",
                str(output_path),
            ],
            check=True,
        )
    return {**result, "status": "ok"}


def get_podcast_gemini(script: str, target: Path, config: Dict[str, Any]) -> Path:
    "Generate the weekly podcast MP3 with configurable Gemini 3.8 TTS."
    output_path = target / f"podcast-{target.name}.mp3"
    if not output_path.exists():
        generate_audio_from_script(script, output_path, config)
    return output_path


def describe_week_files(week: datetime.date, items: List[Dict[str, Any]], target_dir: Path) -> str:
    "Describe what `process_week()` will verify or create for one week."
    return (
        f"Week {week}: {len(items)} messages, "
        f"messages.json={'present' if (target_dir / MESSAGES_JSON_NAME).exists() else 'missing'}, "
        f"messages.txt={'present' if (target_dir / MESSAGES_TEXT_NAME).exists() else 'missing'}, "
        f"podcast-{week}.md={'present' if (target_dir / f'podcast-{week}.md').exists() else 'missing'}, "
        f"podcast-{week}.mp3={'present' if (target_dir / f'podcast-{week}.mp3').exists() else 'missing'}"
    )


def process_week(
    week: datetime.date,
    items: List[Dict[str, Any]],
    config: Dict[str, Any],
    *,
    script_dir: Path | None = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    "Process a week's worth of messages."
    script_dir = script_dir or Path(__file__).parent
    week_dir = script_dir / str(week)
    podcast_script_file = week_dir / f"podcast-{week}.md"
    podcast_audio_file = week_dir / f"podcast-{week}.mp3"

    result: Dict[str, Any] = {
        "week": str(week),
        "message_count": len(items),
        "week_dir": str(week_dir.resolve()),
        "messages_json_path": str((week_dir / MESSAGES_JSON_NAME).resolve()),
        "messages_text_path": str((week_dir / MESSAGES_TEXT_NAME).resolve()),
        "script_path": str(podcast_script_file.resolve()),
        "audio_path": str(podcast_audio_file.resolve()),
    }

    if dry_run:
        result["status"] = "dry-run"
        result["summary"] = describe_week_files(week, items, week_dir)
        return result

    week_dir.mkdir(exist_ok=True)
    messages_json_exists = (week_dir / MESSAGES_JSON_NAME).exists()
    messages_text_exists = (week_dir / MESSAGES_TEXT_NAME).exists()
    write_messages_json_file(week, items, week_dir)
    messages_file = write_messages_file(week, items, week_dir)
    result["messages_json_status"] = "existing" if messages_json_exists else "created"
    result["messages_text_status"] = "existing" if messages_text_exists else "created"

    if not podcast_script_file.exists():
        messages_text = messages_file.read_text(encoding="utf-8")
        previous_scripts = load_previous_scripts(script_dir, week)
        podcast_script = get_podcast_script(messages_text, config, week, previous_scripts)
        podcast_script_file.write_text(podcast_script, encoding="utf-8")
        result["script_status"] = "created"
    else:
        result["script_status"] = "existing"

    if not podcast_audio_file.exists():
        podcast_script = podcast_script_file.read_text(encoding="utf-8")
        get_podcast_gemini(podcast_script, week_dir, config)
        result["audio_status"] = "created"
    else:
        result["audio_status"] = "existing"

    result["status"] = "ok"
    return result


def generate_podcast(weeks: List[datetime.date], script_dir: Path) -> Path:
    """
    Emit an RSS2.0 feed containing one <item> per week, pointing
    at the GitHub release URL for podcast-YYYY-MM-DD.mp3.
    """
    output_path = script_dir / "podcast.xml"
    base_url = "https://github.com/sanand0/generative-ai-group/releases/download/main"
    title = "Generative AI Group Podcast"
    link = "https://github.com/sanand0/generative-ai-group"
    description = "Weekly audio summaries of the Generative AI Group discussions."
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items_xml = []
    for week in sorted(weeks, reverse=True):
        week_label = week.strftime("%Y-%m-%d")
        url = f"{base_url}/podcast-{week_label}.mp3"
        pub = week.strftime("%a, %d %b %Y 00:00:00 GMT")
        md_path = script_dir / week_label / f"podcast-{week_label}.md"
        description_cdata = f"<![CDATA[\n{md_path.read_text(encoding='utf-8')}\n]]>"

        items_xml.append(f"""  <item>
    <title>Week of {week_label}</title>
    <enclosure url="{url}" length="0" type="audio/mpeg"/>
    <guid>{url}</guid>
    <pubDate>{pub}</pubDate>
    <description>{description_cdata}</description>
  </item>""")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>{title}</title>
  <link>{link}</link>
  <description>{description}</description>
  <lastBuildDate>{now}</lastBuildDate>
{chr(10).join(items_xml)}
</channel>
</rss>"""

    output_path.write_text(rss, encoding="utf-8")
    return output_path


def load_config(script_dir: Path) -> Dict[str, Any]:
    "Load `config.toml` from the project root."
    with open(script_dir / "config.toml", "rb") as f:
        return tomllib.load(f)


def load_params(path: str | None) -> Dict[str, Any]:
    "Load command parameters from JSON, optionally from stdin when path is `-`."
    if not path:
        return {}

    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    params = json.loads(raw)
    if not isinstance(params, dict):
        raise ValueError("--params must contain a JSON object")
    return params


def validate_params(params: Dict[str, Any], allowed_keys: Sequence[str]) -> None:
    "Reject unexpected JSON parameters so agent callers fail fast."
    unknown_keys = sorted(set(params) - set(allowed_keys))
    if unknown_keys:
        raise ValueError(f"unsupported params keys: {', '.join(unknown_keys)}")


def resolve_output_format(args: argparse.Namespace) -> str:
    "Resolve text vs JSON output. Non-TTY defaults to JSON for agent callers."
    if args.json:
        return "json"
    if args.format:
        return args.format
    return "text" if sys.stdout.isatty() else "json"


def describe_cli() -> Dict[str, Any]:
    "Return a machine-readable description of the CLI interface."
    return {
        "name": "podcast.py",
        "description": "Generate weekly WhatsApp podcast scripts and chunked Gemini TTS audio.",
        "env": ["OPENAI_API_KEY", "GEMINI_API_KEY"],
        "commands": {
            COMMAND_WEEKLY: {
                "description": "Process grouped weekly messages into transcripts, scripts, audio, and RSS.",
                "params": {
                    "dry_run": {"type": "boolean", "default": False},
                    "format": {"type": "string", "enum": ["text", "json"]},
                    "params": {"type": "json-object", "optional": True},
                },
            },
            COMMAND_TTS_SCRIPT: {
                "description": "Generate audio from a speaker-labeled script using multi-turn Gemini synthesis.",
                "params": {
                    "script_file": {"type": "string", "optional": True},
                    "script": {"type": "string", "optional": True},
                    "audio_out": {"type": "string", "optional": True},
                    "dry_run": {"type": "boolean", "default": False},
                    "format": {"type": "string", "enum": ["text", "json"]},
                    "params": {"type": "json-object", "optional": True},
                },
            },
        },
    }


def summarize_week_result(result: Dict[str, Any]) -> str:
    "Render one weekly result for human-readable CLI output."
    if result["status"] == "dry-run":
        return result["summary"]

    return (
        f"Week {result['week']}: messages.json={result.get('messages_json_status', 'n/a')}, "
        f"messages.txt={result.get('messages_text_status', 'n/a')}, "
        f"script={result.get('script_status', 'n/a')}, "
        f"audio={result.get('audio_status', 'n/a')}"
    )


def emit_result(result: Dict[str, Any], output_format: str) -> None:
    "Print CLI results in text or JSON form."
    if output_format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    command = result.get("command")
    if command == COMMAND_WEEKLY:
        for week_result in result["weeks"]:
            print(summarize_week_result(week_result))
        if result["status"] == "dry-run":
            print(f"Dry run verified {result['week_count']} completed week(s). No API calls were made.")
        else:
            print(f"Generated RSS feed at {result['rss_path']}")
        return

    if command == COMMAND_TTS_SCRIPT:
        if result["status"] == "dry-run":
            print(
                f"Dry run validated {', '.join(result['speaker_names'])} script. "
                f"Would write {result['audio_path']}"
            )
        else:
            print(
                f"Generated audio at {result['audio_path']} using {', '.join(result['speaker_names'])}."
            )
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


def run_weekly(script_dir: Path, *, dry_run: bool) -> Dict[str, Any]:
    "Run the weekly transcript -> script -> audio workflow."
    config = load_config(script_dir)
    groups = load_grouped_messages(script_dir)
    week_results = [
        process_week(week, items, config, script_dir=script_dir, dry_run=dry_run)
        for week, items in groups.items()
    ]

    result: Dict[str, Any] = {
        "command": COMMAND_WEEKLY,
        "status": "dry-run" if dry_run else "ok",
        "week_count": len(groups),
        "weeks": week_results,
    }
    if not dry_run:
        result["rss_path"] = str(generate_podcast(list(groups.keys()), script_dir).resolve())
    return result


def resolve_script_input(
    *,
    script_file: str | None,
    script_text: str | None,
) -> Tuple[str, str]:
    "Resolve exactly one script input source."
    if bool(script_file) == bool(script_text):
        raise ValueError("provide exactly one of --script-file or --script-text")

    if script_file:
        if script_file == "-":
            return sys.stdin.read(), "stdin"
        path = Path(script_file)
        return path.read_text(encoding="utf-8"), str(path.resolve())

    return script_text or "", "inline"


def run_tts_script(
    script_dir: Path,
    *,
    script_file: str | None,
    script_text: str | None,
    audio_out: str | None,
    dry_run: bool,
) -> Dict[str, Any]:
    "Run the script-to-audio workflow for manual testing or ad hoc generation."
    config = load_config(script_dir)
    script, source = resolve_script_input(script_file=script_file, script_text=script_text)

    if audio_out:
        output_path = Path(audio_out)
    elif script_file and script_file != "-":
        output_path = Path(script_file).with_suffix(".mp3")
    else:
        raise ValueError("--audio-out is required when using --script-text or stdin")

    result = generate_audio_from_script(script, output_path, config, dry_run=dry_run)
    result["script_source"] = source
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate weekly podcast assets from WhatsApp exports or synthesize audio "
            "from a speaker-labeled script using multi-turn Gemini TTS."
        )
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=[COMMAND_WEEKLY, COMMAND_TTS_SCRIPT],
        default=COMMAND_WEEKLY,
        help="`weekly` processes grouped WhatsApp weeks; `tts-script` renders a script in conversational chunks",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and planned outputs without writing files or calling APIs",
    )
    parser.add_argument(
        "--params",
        help="Read command parameters from a JSON object file, or `-` for stdin",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        help="Output format. Defaults to JSON for non-TTY callers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Shortcut for `--format json`",
    )
    parser.add_argument(
        "--describe",
        action="store_true",
        help="Print a machine-readable CLI schema as JSON and exit",
    )
    parser.add_argument(
        "--script-file",
        help="Path to a speaker-labeled script for `tts-script`, or `-` for stdin",
    )
    parser.add_argument(
        "--script-text",
        help="Inline speaker-labeled script text for `tts-script`",
    )
    parser.add_argument(
        "--audio-out",
        help="Output audio path for `tts-script`. Defaults to the script filename with `.mp3`.",
    )
    return parser


def main(argv: List[str] | None = None, *, script_dir: Path | None = None) -> int:
    "Main function to process messages and generate podcasts."
    args = build_parser().parse_args(argv)
    output_format = resolve_output_format(args)
    script_dir = script_dir or Path(__file__).parent

    if args.describe:
        emit_result(describe_cli(), "json")
        return 0

    params = load_params(args.params)

    try:
        if args.command == COMMAND_WEEKLY:
            validate_params(params, ["dry_run"])
            dry_run = bool(params.get("dry_run", args.dry_run))
            result = run_weekly(script_dir, dry_run=dry_run)
        else:
            validate_params(params, ["audio_out", "dry_run", "script", "script_file"])
            dry_run = bool(params.get("dry_run", args.dry_run))
            script_file = args.script_file or params.get("script_file")
            script_text = args.script_text or params.get("script")
            audio_out = args.audio_out or params.get("audio_out")
            result = run_tts_script(
                script_dir,
                script_file=script_file,
                script_text=script_text,
                audio_out=audio_out,
                dry_run=dry_run,
            )
    except Exception as exc:
        error_result = {
            "command": args.command,
            "status": "error",
            "error": str(exc),
        }
        emit_result(error_result, output_format)
        return 1

    emit_result(result, output_format)
    return 0


if __name__ == "__main__":
    load_dotenv()
    raise SystemExit(main())
