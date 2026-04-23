#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
# ]
# ///

import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

import requests

MESSAGES_JSON_NAME = "messages.json"
MESSAGES_TEXT_NAME = "messages.txt"
WEEK_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
COMMAND_WEEKLY = "weekly"
COMMAND_TTS_SCRIPT = "tts-script"
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-tts-preview"
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


@dataclass(frozen=True)
class SpeakerConfig:
    "Speaker metadata used to validate scripts and build Gemini voice settings."

    name: str
    voice_name: str
    profile: str = ""


def raise_for_status_with_body(response: Any) -> None:
    "Raise for HTTP status, echoing the raw API body to stderr for debugging."

    try:
        response.raise_for_status()
    except Exception:
        body = getattr(response, "text", "").strip()
        if body:
            print(body, file=sys.stderr)
        raise


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


def render_script_prompt(config: Dict[str, Any], week: datetime.date) -> str:
    "Render the OpenAI script-writing prompt for the requested week."
    return config["podcast"].replace("$WEEK", week.strftime("%d %B %Y"))


def get_podcast_script(
    messages_text: str, config: Dict[str, Any], week: datetime.date
) -> Tuple[float, str]:
    "Generate a podcast script using the OpenAI Responses API."
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY is not set")

    prompt = render_script_prompt(config, week)

    payload = {
        "model": DEFAULT_OPENAI_MODEL,
        "input": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": messages_text},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
    }

    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers=headers,
        json=payload,
        timeout=180,
    )
    raise_for_status_with_body(response)
    result = response.json()
    cost = result["usage"]["input_tokens"] * 0.4 + result["usage"]["output_tokens"] * 1.6
    return cost, result["output"][-1]["content"][0]["text"]


def collapse_whitespace(text: str) -> str:
    "Collapse internal whitespace to keep prompt scaffolding compact."
    return re.sub(r"\s+", " ", text.strip())


def load_gemini_speakers(config: Dict[str, Any]) -> List[SpeakerConfig]:
    "Load Gemini speaker definitions from config.toml."
    speaker_items = config.get("gemini", {}).get("speakers")
    if not isinstance(speaker_items, list) or not speaker_items:
        raise ValueError("config.toml must define `[[gemini.speakers]]` entries")

    speakers = [
        SpeakerConfig(
            name=item["name"],
            voice_name=item["voice_name"],
            profile=str(item.get("profile", "")).strip(),
        )
        for item in speaker_items
    ]
    if len(speakers) > 2:
        raise ValueError("Gemini multi-speaker TTS supports at most 2 speakers")

    return speakers


def normalize_script(script: str, allowed_speakers: Sequence[str]) -> Tuple[str, List[str]]:
    """
    Normalize a speaker-labeled transcript into one utterance per line.

    Each non-empty line must either start with `Speaker:` or continue the previous speaker's text.
    """

    if not script.strip():
        raise ValueError("script is empty")

    speaker_pattern = re.compile(
        rf"^(?P<speaker>{'|'.join(re.escape(name) for name in allowed_speakers)}):\s*(?P<text>.*)$"
    )
    generic_label_pattern = re.compile(r"^(?P<label>[^:\s][^:]{0,80}):\s*(?P<text>.*)$")

    utterances: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None

    for index, raw_line in enumerate(script.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        speaker_match = speaker_pattern.match(line)
        if speaker_match:
            current = {
                "speaker": speaker_match.group("speaker"),
                "text": speaker_match.group("text").strip(),
            }
            utterances.append(current)
            continue

        generic_match = generic_label_pattern.match(line)
        if generic_match:
            raise ValueError(
                f"line {index} uses unsupported speaker {generic_match.group('label')!r}; "
                f"expected one of {', '.join(allowed_speakers)}"
            )

        if current is None:
            raise ValueError(
                f"line {index} must begin with a speaker label like {allowed_speakers[0]}:"
            )

        if current["text"]:
            current["text"] += " " + line
        else:
            current["text"] = line

    if not utterances:
        raise ValueError("script has no speaker lines")

    used_speakers: List[str] = []
    normalized_lines: List[str] = []
    for utterance in utterances:
        text = utterance["text"].strip()
        if not text:
            raise ValueError(f"speaker {utterance['speaker']} has an empty line in the script")
        normalized_lines.append(f"{utterance['speaker']}: {text}")
        if utterance["speaker"] not in used_speakers:
            used_speakers.append(utterance["speaker"])

    return "\n".join(normalized_lines), used_speakers


def split_script_segments(
    script: str, config: Dict[str, Any]
) -> Tuple[List[Tuple[SpeakerConfig, str]], str, List[SpeakerConfig]]:
    "Split a validated script into one normalized Gemini request per spoken line."
    all_speakers = load_gemini_speakers(config)
    speaker_by_name = {speaker.name: speaker for speaker in all_speakers}
    normalized_script, used_speakers = normalize_script(script, list(speaker_by_name))
    segments = []
    for line in normalized_script.splitlines():
        speaker_name, text = line.split(":", 1)
        segments.append((speaker_by_name[speaker_name], text.strip()))
    return segments, normalized_script, [speaker_by_name[name] for name in used_speakers]


def build_tts_prompt(text: str, speaker: SpeakerConfig, config: Dict[str, Any]) -> str:
    "Build a Gemini TTS prompt for one speaker line."
    sections = [
        "Synthesize speech for the following podcast line.",
        "Do not read these instructions aloud.",
        "Honor inline audio tags such as [excited], [laughs], [whispers], and [short pause].",
        "Only speak the transcript under the TRANSCRIPT heading.",
    ]

    podcast_style = collapse_whitespace(str(config.get("podcast_style", "")))
    if podcast_style:
        sections.append(podcast_style)

    if speaker.profile.strip():
        sections.append(f"Speaker guidance: {collapse_whitespace(speaker.profile)}")

    sections.append("TRANSCRIPT")
    sections.append(text.strip())
    return "\n".join(sections)


def build_gemini_request(text: str, speaker: SpeakerConfig, config: Dict[str, Any]) -> Dict[str, Any]:
    "Build a single-speaker Gemini TTS request payload for one line."
    return {
        "model": config.get("gemini", {}).get("model", DEFAULT_GEMINI_MODEL),
        "contents": [
            {
                "role": "user",
                "parts": [{"text": build_tts_prompt(text, speaker, config)}],
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": speaker.voice_name,
                    }
                }
            },
        },
    }


def request_gemini_audio(payload: Dict[str, Any]) -> bytes:
    "Call the Gemini TTS endpoint and return raw PCM bytes."
    if not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is not set")

    headers = {
        "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        "Content-Type": "application/json",
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{payload['model']}:generateContent"
    )

    response = None
    for attempt in range(1, 4):
        response = requests.post(url, headers=headers, json=payload, timeout=300)
        try:
            raise_for_status_with_body(response)
            break
        except requests.HTTPError:
            if response.status_code not in RETRYABLE_STATUS_CODES or attempt == 3:
                raise
            time.sleep(attempt)

    result = response.json()
    audio_b64 = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    return base64.b64decode(audio_b64)


def render_pcm_as_mp3(audio_pcm: bytes, output_path: Path, config: Dict[str, Any]) -> Path:
    "Convert raw 24kHz mono PCM from Gemini into the configured audio format."
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pcm_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".pcm", dir=output_path.parent
        ) as temp_file:
            temp_file.write(audio_pcm)
            pcm_path = Path(temp_file.name)

        ffmpeg_args = [
            arg.format(pcm=pcm_path, output=output_path)
            for arg in config["gemini"]["ffmpeg_command"]
        ]
        subprocess.run(ffmpeg_args, check=True)
    finally:
        if pcm_path and pcm_path.exists():
            pcm_path.unlink()

    return output_path


def concatenate_audio_files(segment_paths: Sequence[Path], output_path: Path) -> Path:
    "Concatenate per-line MP3 clips into the final podcast output."
    output_path.parent.mkdir(parents=True, exist_ok=True)

    list_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            suffix=".txt",
            dir=output_path.parent,
            encoding="utf-8",
        ) as temp_file:
            temp_file.write(
                "\n".join(f"file '{segment_path.resolve()}'" for segment_path in segment_paths)
            )
            list_path = Path(temp_file.name)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-c:a",
                "libmp3lame",
                "-qscale:a",
                "5",
                "-ar",
                "44100",
                "-ac",
                "1",
                "-id3v2_version",
                "3",
                str(output_path),
            ],
            check=True,
        )
    finally:
        if list_path and list_path.exists():
            list_path.unlink()

    return output_path


def generate_audio_from_script(
    script: str,
    output_path: Path,
    config: Dict[str, Any],
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    "Generate audio for a speaker-labeled podcast script."
    segments, normalized_script, speakers = split_script_segments(script, config)
    result = {
        "command": COMMAND_TTS_SCRIPT,
        "audio_path": str(output_path.resolve()),
        "speaker_names": [speaker.name for speaker in speakers],
        "segment_count": len(segments),
        "model": config.get("gemini", {}).get("model", DEFAULT_GEMINI_MODEL),
        "normalized_script": normalized_script,
    }

    if dry_run:
        result["status"] = "dry-run"
        return result

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_path.parent) as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        segment_paths = []
        for index, (speaker, text) in enumerate(segments, start=1):
            segment_path = temp_dir / f"{index:03d}.mp3"
            audio_pcm = request_gemini_audio(build_gemini_request(text, speaker, config))
            render_pcm_as_mp3(audio_pcm, segment_path, config)
            segment_paths.append(segment_path)
        concatenate_audio_files(segment_paths, output_path)

    result["status"] = "ok"
    return result


def get_podcast_gemini(script: str, target: Path, config: Dict[str, Any]) -> Path:
    "Generate the weekly podcast audio file using per-line Gemini TTS plus concatenation."
    output_path = target / f"podcast-{target.name}.mp3"
    if output_path.exists():
        return output_path

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
        cost, podcast_script = get_podcast_script(messages_text, config, week)
        podcast_script_file.write_text(podcast_script, encoding="utf-8")
        result["script_status"] = "created"
        result["script_cost_cents"] = round(cost / 1e4, 4)
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
        "description": "Generate weekly WhatsApp podcast scripts and segmented Gemini TTS audio.",
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
                "description": "Generate audio from a speaker-labeled script using per-line Gemini synthesis and concatenation.",
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

    cost_text = ""
    if "script_cost_cents" in result:
        cost_text = f", script_cost={result['script_cost_cents']}c"

    return (
        f"Week {result['week']}: messages.json={result.get('messages_json_status', 'n/a')}, "
        f"messages.txt={result.get('messages_text_status', 'n/a')}, "
        f"script={result.get('script_status', 'n/a')}, "
        f"audio={result.get('audio_status', 'n/a')}{cost_text}"
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
            "from a speaker-labeled script using line-by-line Gemini TTS."
        )
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=[COMMAND_WEEKLY, COMMAND_TTS_SCRIPT],
        default=COMMAND_WEEKLY,
        help="`weekly` processes grouped WhatsApp weeks; `tts-script` renders a script line by line",
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
    raise SystemExit(main())
