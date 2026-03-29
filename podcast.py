#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
#     "tqdm",
# ]
# ///

import datetime
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

MESSAGES_JSON_NAME = "messages.json"
MESSAGES_TEXT_NAME = "messages.txt"
WEEK_DIR_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


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
    "Load and filter messages from JSON file"
    with open(filepath, encoding="utf-8") as f:
        return [m for m in json.load(f) if m.get("time") and m.get("text") and m.get("author")]


def group_by_week(messages: List[Dict[str, Any]]) -> Dict[datetime.date, List[Dict[str, Any]]]:
    "Group messages by ISO-week (Sunday to Saturday, UTC)"
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
    "Build message threads from items"
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
    "Render a message and its replies to a file"
    indent = "  " * lvl
    line = f"{indent}- {message['author']}: {message['text'].replace(chr(10), ' ')}"
    if message.get("reactions"):
        line += f" [{message['reactions']}]"
    file.write(line + "\n")
    for r in sorted(replies_dict[message["messageId"]], key=lambda x: x["dt"]):
        render_message(r, replies_dict, file, lvl + 1)


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
    "Write messages to a file in the target directory"
    target_dir.mkdir(exist_ok=True)
    messages_file = target_dir / MESSAGES_TEXT_NAME

    if messages_file.exists():
        return messages_file

    replies, roots = build_threads(items)
    with open(messages_file, "w", encoding="utf-8") as f:
        for r in roots:
            render_message(r, replies, f)
    return messages_file


def get_podcast_script(
    messages_text: str, config: Dict[str, Any], week: datetime.date
) -> Tuple[float, str]:
    "Generate a podcast script using OpenAI API"
    import requests

    prompt = config["podcast"].replace("$WEEK", week.strftime("%d %B %Y"))

    payload = {
        "model": "gpt-5.4-mini",
        "input": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": messages_text},
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
    }

    response = requests.post("https://api.openai.com/v1/responses", headers=headers, json=payload)
    raise_for_status_with_body(response)
    result = response.json()
    cost = result["usage"]["input_tokens"] * 0.4 + result["usage"]["output_tokens"] * 1.6
    # Use last .output entry - first few have reasoning
    return cost, result["output"][-1]["content"][0]["text"]


def generate_podcast_audio(script: str, target_dir: Path, config: Dict[str, Any]) -> None:
    "Generate speech files for each line in the podcast script"
    import requests
    from tqdm import tqdm

    speakers = {k: v for k, v in config.items() if isinstance(v, dict) and "voice" in v}
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }

    # Pattern: speaker name, optional annotation (max 25 chars), then colon
    speaker_pattern = re.compile(rf"^({'|'.join(re.escape(s) for s in speakers)}).{{0,25}}:")

    raw_lines = [ln.strip() for ln in script.splitlines() if ln.strip()]
    # Concatenate lines without a speaker to the previous line
    lines = []
    for line in raw_lines:
        if speaker_pattern.match(line):
            lines.append(line)
        elif lines:
            lines[-1] += "\n" + line

    filenames = []
    for line in tqdm(lines, desc="Generating speech"):
        match = speaker_pattern.match(line)
        speaker = match.group(1)
        podcast_filename = target_dir / f"{len(filenames) + 1:03d}.opus"
        filenames.append(podcast_filename)
        if podcast_filename.exists():
            continue
        text = line[match.end():].strip()
        body = {
            "model": "gpt-audio-mini",
            "input": text,
            "voice": speakers[speaker]["voice"],
            "instructions": speakers[speaker]["instructions"],
            "response_format": "opus",
        }
        r = requests.post("https://api.openai.com/v1/audio/speech", headers=headers, json=body)
        raise_for_status_with_body(r)
        with open(podcast_filename, "wb") as f:
            f.write(r.content)

    # Concatenate all audio files
    list_file = target_dir / "list.txt"
    list_file.write_text("\n".join(f"file '{f.name}'" for f in filenames))
    concat = f"ffmpeg -y -f concat -i {list_file} -safe 0 -c:a libmp3lame -qscale:a 5 -ar 44100 -ac 1 -id3v2_version 3 {target_dir / f'podcast-{target_dir.name}.mp3'}"
    os.system(concat)
    list_file.unlink()


def get_podcast_gemini(script, target, config):
    """Generate a podcast audio file using Gemini 2.5 Flash Preview TTS."""
    import requests

    output_path = target / f"podcast-{target.name}.mp3"
    if output_path.exists():
        return output_path

    script_text = f"{config['podcast_style']}\n\n{script.strip()}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": script_text}]}],
        "generationConfig": config["gemini"]["generation_config"],
    }
    headers = {
        "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        "Content-Type": "application/json",
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.5-flash-preview-tts:generateContent"
    )
    response = requests.post(url, headers=headers, json=payload)
    raise_for_status_with_body(response)
    result = response.json()
    json_path = target / "gemini-audio.json"
    json_path.write_text(json.dumps(result, indent=2))

    audio_b64 = result["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    pcm_path = target / "podcast.pcm"
    audio_pcm = base64.b64decode(audio_b64)
    pcm_path.write_bytes(audio_pcm)
    ffmpeg_args = [
        arg.format(pcm=pcm_path, output=output_path) for arg in config["gemini"]["ffmpeg_command"]
    ]
    subprocess.run(ffmpeg_args, check=True)
    pcm_path.unlink()
    json_path.unlink()

    return output_path


def describe_week_files(week: datetime.date, items: List[Dict[str, Any]], target_dir: Path) -> str:
    "Describe what `process_week()` will verify or create for one week."
    return (
        f"Week {week}: {len(items)} messages, "
        f"messages.json={'present' if (target_dir / MESSAGES_JSON_NAME).exists() else 'missing'}, "
        f"messages.txt={'present' if (target_dir / MESSAGES_TEXT_NAME).exists() else 'missing'}, "
        f"podcast.md={'present' if (target_dir / f'podcast-{week}.md').exists() else 'missing'}, "
        f"podcast.mp3={'present' if (target_dir / f'podcast-{week}.mp3').exists() else 'missing'}"
    )


def process_week(
    week: datetime.date,
    items: List[Dict[str, Any]],
    config: Dict[str, Any],
    *,
    script_dir: Path | None = None,
    dry_run: bool = False,
) -> None:
    "Process a week's worth of messages"
    script_dir = script_dir or Path(__file__).parent
    week_dir = script_dir / str(week)

    if dry_run:
        print(describe_week_files(week, items, week_dir))
        return

    week_dir.mkdir(exist_ok=True)

    podcast_script_file = week_dir / f"podcast-{week}.md"
    podcast_audio_file = week_dir / f"podcast-{week}.mp3"

    write_messages_json_file(week, items, week_dir)
    messages_file = write_messages_file(week, items, week_dir)

    # Generate podcast script if it doesn't exist
    if not podcast_script_file.exists():
        messages_text = messages_file.read_text()
        cost, podcast_script = get_podcast_script(messages_text, config, week)
        print(f"Week {week}: Podcast script cost: {cost / 1e4:,.1f}c")
        with open(podcast_script_file, "w") as f:
            f.write(podcast_script)

    # Generate podcast audio if it doesn't exist
    if not podcast_audio_file.exists():
        podcast_script = podcast_script_file.read_text()
        get_podcast_gemini(podcast_script, week_dir, config)
        print(f"Week {week}: Generated podcast audio at {podcast_audio_file}")


def generate_podcast(weeks: List[datetime.date], script_dir: Path) -> None:
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

    # build each <item>
    items_xml = []
    for week in sorted(weeks, reverse=True):
        d = week.strftime("%Y-%m-%d")
        url = f"{base_url}/podcast-{d}.mp3"
        # RFC-822 pubDate at midnight UTC on the week start
        pub = week.strftime("%a, %d %b %Y 00:00:00 GMT")
        # Load script
        md_path = script_dir / d / f"podcast-{d}.md"
        description_cdata = f"<![CDATA[\n{md_path.read_text(encoding='utf-8')}\n]]>"

        items_xml.append(f"""  <item>
    <title>Week of {d}</title>
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate weekly podcast assets from WhatsApp exports. Week inputs are "
            "stored in YYYY-MM-DD/messages.json, and --dry-run verifies the weekly "
            "plan without writing files or making LLM/TTS API calls."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify weekly grouping and file status without writing files or calling APIs",
    )
    return parser


def main(argv: List[str] | None = None, *, script_dir: Path | None = None) -> int:
    "Main function to process messages and generate podcasts"
    args = build_parser().parse_args(argv)
    script_dir = script_dir or Path(__file__).parent

    # Load config
    with open(script_dir / "config.toml", "rb") as f:
        config = tomllib.load(f)

    # Load and process messages
    groups = load_grouped_messages(script_dir)

    # Process each week
    for week, items in groups.items():
        process_week(week, items, config, script_dir=script_dir, dry_run=args.dry_run)

    # Generate RSS feed
    if args.dry_run:
        print(f"Dry run verified {len(groups)} completed week(s). No API calls were made.")
        return 0

    generate_podcast(weeks=list(groups.keys()), script_dir=script_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
