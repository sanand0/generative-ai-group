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
    "Group messages by ISO-week (Monday)"
    groups = defaultdict(list)
    for m in messages:
        dt = datetime.datetime.fromisoformat(m["time"].replace("Z", "+00:00"))
        m["dt"] = dt
        week = dt.date() - datetime.timedelta(days=dt.weekday())
        groups[week].append(m)
    return groups


def build_threads(
    items: List[Dict[str, Any]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    "Build message threads from items"
    by_id = {m["messageId"]: m for m in items}
    replies = defaultdict(list)
    for m in items:
        pid = m.get("quoteMessageId")
        if pid in by_id:
            replies[pid].append(m)
    roots = [m for m in items if m.get("quoteMessageId") not in by_id]
    roots.sort(key=lambda m: m["dt"])
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
    concat = f"ffmpeg -y -f concat -i {list_file} -safe 0 -c:a libmp3lame -qscale:a 5 -ar 44100 -ac 1 -id3v2_version 3 {target_dir / 'podcast.mp3'}"
    os.system(concat)
    list_file.unlink()


def process_week(week: datetime.date, items: List[Dict[str, Any]], config: Dict[str, Any]) -> None:
    "Process a week's worth of messages"
    script_dir = Path(__file__).parent
    week_dir = script_dir / str(week)
    week_dir.mkdir(exist_ok=True)

    podcast_script_file = week_dir / "podcast.md"
    podcast_audio_file = week_dir / "podcast.mp3"

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


if __name__ == "__main__":
    main()
