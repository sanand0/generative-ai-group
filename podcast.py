#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "requests",
#     "tqdm",
# ]
# ///

import json
import os
import datetime
import requests
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Tuple
from tqdm import tqdm


def load_messages(filepath: str) -> List[Dict[str, Any]]:
    "Load and filter messages from JSON file"
    with open(filepath) as f:
        return [m for m in json.load(f) if m.get("time") and m.get("text") and m.get("author")]


def group_by_week(messages: List[Dict[str, Any]]) -> Dict[datetime.date, List[Dict[str, Any]]]:
    "Group messages by ISO-week (Sunday to Saturday, UTC)"
    groups = defaultdict(list)
    for message in messages:
        dt = datetime.datetime.fromisoformat(message["time"].replace("Z", "+00:00"))
        days_since_sunday = dt.isoweekday() % 7
        week_start = dt.date() - datetime.timedelta(days=days_since_sunday)
        message["dt"] = dt
        groups[week_start].append(message)
    return groups


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


def write_messages_file(week: datetime.date, items: List[Dict[str, Any]], target_dir: Path) -> Path:
    "Write messages to a file in the target directory"
    target_dir.mkdir(exist_ok=True)
    messages_file = target_dir / "messages.txt"

    if messages_file.exists():
        return messages_file

    replies, roots = build_threads(items)
    with open(messages_file, "w") as f:
        for r in roots:
            render_message(r, replies, f)
    return messages_file


def get_podcast_script(
    messages_text: str, config: Dict[str, Any], week: datetime.date
) -> Tuple[float, str]:
    "Generate a podcast script using OpenAI API"
    prompt = config["podcast"].replace("$WEEK", week.strftime("%d %b %Y"))

    payload = {
        "model": "gpt-4.1-mini",
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
    response.raise_for_status()
    result = response.json()
    cost = result["usage"]["input_tokens"] * 0.4 + result["usage"]["output_tokens"] * 1.6
    return cost, result["output"][0]["content"][0]["text"]


def generate_podcast_audio(script: str, target_dir: Path, config: Dict[str, Any]) -> None:
    "Generate speech files for each line in the podcast script"
    speakers = {k: v for k, v in config.items() if isinstance(v, dict) and "voice" in v}
    headers = {
        "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
        "Content-Type": "application/json",
    }

    lines = [ln.strip() for ln in script.splitlines() if ln.strip()]
    filenames = []
    for line in tqdm(lines, desc="Generating speech"):
        # Skip lines without valid speaker
        speaker = next((s for s in speakers if line.startswith(f"{s}:")), None)
        if speaker is None:
            continue
        podcast_filename = target_dir / f"{len(filenames) + 1:03d}.opus"
        filenames.append(podcast_filename)
        if podcast_filename.exists():
            continue
        text = line[len(speaker) + 1 :].strip()
        body = {
            "model": "gpt-4o-mini-tts",
            "input": text,
            "voice": speakers[speaker]["voice"],
            "instructions": speakers[speaker]["instructions"],
            "response_format": "opus",
        }
        r = requests.post("https://api.openai.com/v1/audio/speech", headers=headers, json=body)
        r.raise_for_status()
        with open(podcast_filename, "wb") as f:
            f.write(r.content)

    # Concatenate all audio files
    list_file = target_dir / "list.txt"
    list_file.write_text("\n".join(f"file '{f.name}'" for f in filenames))
    concat = f"ffmpeg -y -f concat -i {list_file} -safe 0 -c:a libmp3lame -qscale:a 5 -ar 44100 -ac 1 -id3v2_version 3 {target_dir / f'podcast-{target_dir.name}.mp3'}"
    os.system(concat)
    list_file.unlink()


def process_week(week: datetime.date, items: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    "Process a week's worth of messages"
    script_dir = Path(__file__).parent
    week_dir = script_dir / str(week)
    week_dir.mkdir(exist_ok=True)

    podcast_script_file = week_dir / f"podcast-{week}.md"
    podcast_audio_file = week_dir / f"podcast-{week}.mp3"

    # Write messages file if it doesn't exist
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
        generate_podcast_audio(podcast_script, week_dir, config)
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


def main() -> None:
    "Main function to process messages and generate podcasts"
    script_dir = Path(__file__).parent

    # Load config
    with open(script_dir / "config.toml", "rb") as f:
        config = tomllib.load(f)

    # Load and process messages
    messages = load_messages("gen-ai-messages.json")
    groups = group_by_week(messages)

    # Process each week
    for week, items in groups.items():
        process_week(week, items, config)

    # Generate RSS feed
    generate_podcast(weeks=list(groups.keys()), script_dir=script_dir)


if __name__ == "__main__":
    main()
