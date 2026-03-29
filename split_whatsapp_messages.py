#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

LEGACY_MONTH_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}\.json$")
WEEK_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
TIME_PREFIX_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T")
MESSAGES_JSON_NAME = "messages.json"
LEGACY_MESSAGES_DIR = "messages"
UNKNOWN_TIME_DIRNAME = "unknown-time"


def compact_message(message: dict[str, Any]) -> dict[str, Any]:
    """Drop empty scraper fields so old exports behave like current ones."""

    return {
        key: value
        for key, value in message.items()
        if value is not None and value is not False and value != ""
    }


def merge_value(previous: Any, next_value: Any, key: str) -> Any:
    """Mirror the scraper's field-aware merge rules for repeated message IDs."""

    if next_value is None or next_value is False or next_value == "":
        return previous
    if previous is None or previous is False or previous == "":
        return next_value

    if isinstance(previous, bool) and isinstance(next_value, bool):
        return previous or next_value

    if isinstance(previous, int | float) and isinstance(next_value, int | float):
        return next_value if next_value > previous else previous

    if isinstance(previous, str) and isinstance(next_value, str):
        if key == "reactions" and next_value != previous:
            return next_value
        if len(next_value) > len(previous):
            return next_value
        if (
            len(next_value) == len(previous)
            and next_value != previous
            and key in {"time", "mediaDuration"}
        ):
            return next_value

    return previous


def parse_message_array(raw_text: str, path: Path) -> list[dict[str, Any]]:
    """Load a WhatsApp export array, repairing a missing outer `[` when needed."""

    stripped = raw_text.lstrip("\ufeff \t\r\n")
    candidates = [stripped]

    repaired = stripped
    if not repaired.startswith("["):
        repaired = f"[{repaired}"
    if not repaired.rstrip().endswith("]"):
        repaired = f"{repaired.rstrip()}]"
    if repaired != stripped:
        candidates.append(repaired)

    last_error: json.JSONDecodeError | None = None
    for candidate in candidates:
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(loaded, list):
            if not all(isinstance(message, dict) for message in loaded):
                raise ValueError(f"{path} must contain an array of objects")
            return loaded
        raise ValueError(f"{path} must contain a JSON array")

    detail = f": {last_error}" if last_error else ""
    raise ValueError(f"Could not parse {path}{detail}")


def load_messages(path: Path) -> list[dict[str, Any]]:
    """Load and normalize one exported WhatsApp message file."""

    loaded = parse_message_array(path.read_text(encoding="utf-8"), path)
    return [compact_message(dict(message)) for message in loaded]


def merge_messages(messages: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge messages by `messageId` using the scraper's field-aware rules."""

    merged_by_id: dict[str, dict[str, Any]] = {}

    for message in messages:
        message_id = message.get("messageId")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError(f"Each message must have a non-empty string messageId: {message}")

        merged = merged_by_id.setdefault(message_id, {})
        for key, value in compact_message(message).items():
            merged[key] = merge_value(merged.get(key), value, key)

    return sorted(
        (compact_message(message) for message in merged_by_id.values()),
        key=lambda message: (message.get("time") or "", message["messageId"]),
    )


def parse_message_time(message: dict[str, Any]) -> dt.datetime | None:
    """Parse a message's ISO timestamp, returning `None` for legacy null/malformed rows."""

    time = message.get("time")
    if not isinstance(time, str) or not TIME_PREFIX_PATTERN.match(time):
        return None
    return dt.datetime.fromisoformat(time.replace("Z", "+00:00"))


def week_bucket(message: dict[str, Any], *, today: dt.date) -> str | None:
    """
    Return the output bucket for a message using `podcast.py`'s weekly labeling.

    `podcast.py` computes `week_end` as:

    - parse the UTC message timestamp
    - add `7 - (isoweekday % 7)` days

    That means Monday-Saturday messages go into the coming Sunday's file, and Sunday
    messages go into the following Sunday's file. If that computed Sunday is after
    `today`, the week is still in progress, so the message is held back to match
    `podcast.py`'s `group_by_week()` behavior. Messages without a parseable ISO time
    go to `unknown-time/messages.json`.
    """

    message_time = parse_message_time(message)
    if message_time is None:
        return UNKNOWN_TIME_DIRNAME

    days_until_sunday = 7 - (message_time.isoweekday() % 7)
    week_end = message_time.date() + dt.timedelta(days=days_until_sunday)
    if week_end > today:
        return None
    return week_end.isoformat()


def existing_output_files(output_root: Path) -> list[Path]:
    """List new-style and legacy shard files so reruns can merge existing output first."""

    if not output_root.exists():
        return []

    output_files: list[Path] = []
    for child in output_root.iterdir():
        if not child.is_dir():
            continue
        if child.name == UNKNOWN_TIME_DIRNAME or WEEK_FILE_PATTERN.match(f"{child.name}.json"):
            messages_json = child / MESSAGES_JSON_NAME
            if messages_json.is_file():
                output_files.append(messages_json)

    legacy_output_dir = output_root / LEGACY_MESSAGES_DIR
    if legacy_output_dir.exists():
        for legacy_file in legacy_output_dir.iterdir():
            if legacy_file.is_file() and (
                WEEK_FILE_PATTERN.match(legacy_file.name)
                or LEGACY_MONTH_FILE_PATTERN.match(legacy_file.name)
                or legacy_file.name == "unknown-time.json"
            ):
                output_files.append(legacy_file)

    return sorted(output_files)


def output_path_for_bucket(output_root: Path, bucket: str) -> Path:
    """Return the canonical messages.json path for a weekly output bucket."""

    return output_root / bucket / MESSAGES_JSON_NAME


def render_messages_json(rows: list[dict[str, Any]]) -> str:
    """Serialize rows exactly as this tool persists weekly shard files."""

    return json.dumps(rows, ensure_ascii=False, indent=2) + "\n"


def verify_split_integrity(
    output_root: Path,
    expected_outputs: dict[Path, list[dict[str, Any]]],
    deferred_messages: list[dict[str, Any]],
    merged_messages: list[dict[str, Any]],
) -> None:
    """
    Confirm every merged message is either written to disk or intentionally deferred.

    Deferred messages are the current/future-week rows that `podcast.py` also skips
    until their Sunday-labeled shard is complete.
    """

    actual_output_paths = set(existing_output_files(output_root))
    expected_output_paths = set(expected_outputs)
    if actual_output_paths != expected_output_paths:
        raise ValueError(
            "Output shard mismatch: "
            f"expected {sorted(str(path.relative_to(output_root)) for path in expected_output_paths)}, "
            f"found {sorted(str(path.relative_to(output_root)) for path in actual_output_paths)}"
        )

    mismatched_paths: list[str] = []
    written_message_ids: set[str] = set()
    for output_path, expected_rows in sorted(expected_outputs.items()):
        actual_rows = load_messages(output_path)
        if actual_rows != expected_rows:
            mismatched_paths.append(str(output_path.relative_to(output_root)))
        written_message_ids.update(message["messageId"] for message in actual_rows)

    deferred_message_ids = {message["messageId"] for message in deferred_messages}
    merged_message_ids = {message["messageId"] for message in merged_messages}

    lost_message_ids = sorted(merged_message_ids - written_message_ids - deferred_message_ids)
    unexpected_message_ids = sorted(written_message_ids - merged_message_ids)
    duplicated_message_ids = sorted(written_message_ids & deferred_message_ids)
    if mismatched_paths or lost_message_ids or unexpected_message_ids or duplicated_message_ids:
        details = []
        if mismatched_paths:
            details.append(f"Output mismatch: {sorted(mismatched_paths)}")
        if lost_message_ids:
            details.append(f"Lost messages: {lost_message_ids}")
        if unexpected_message_ids:
            details.append(f"Unexpected messages: {unexpected_message_ids}")
        if duplicated_message_ids:
            details.append(f"Written and deferred: {duplicated_message_ids}")
        raise ValueError("; ".join(details))


def split_messages(
    input_paths: Iterable[Path],
    output_root: Path = Path("."),
    *,
    today: dt.date | None = None,
) -> list[Path]:
    """
    Merge input files plus existing outputs, then rewrite weekly shards.

    Weekly shard filenames match `podcast.py`'s `group_by_week()` output:

    - dated files are `YYYY-MM-DD/messages.json`
    - `YYYY-MM-DD` is the Sunday label computed by `podcast.py`
    - Monday-Saturday messages are written to the coming Sunday file
    - Sunday messages are written to the following Sunday file
    - weeks whose computed Sunday is after today's UTC date are skipped for now
    - messages without a parseable ISO timestamp are preserved in
      `unknown-time/messages.json`

    If a target output file already exists, it is treated as the first input so fresh
    data can enrich older partial rows instead of replacing them wholesale.
    Returns only the shard paths whose contents changed on disk.
    """

    normalized_inputs = [path.resolve() for path in input_paths]
    if not normalized_inputs:
        raise ValueError("Provide at least one input JSON file")

    output_root = output_root.resolve()
    today = today or dt.datetime.now(dt.timezone.utc).date()
    prior_outputs = existing_output_files(output_root)

    merged_messages = merge_messages(
        message
        for path in [*prior_outputs, *normalized_inputs]
        for message in load_messages(path)
    )

    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    deferred_messages: list[dict[str, Any]] = []
    for message in merged_messages:
        bucket = week_bucket(message, today=today)
        if bucket is None:
            deferred_messages.append(message)
            continue
        buckets[bucket].append(message)

    output_root.mkdir(parents=True, exist_ok=True)
    expected_outputs: dict[Path, list[dict[str, Any]]] = {}
    modified_paths: list[Path] = []
    for bucket, rows in sorted(buckets.items()):
        output_path = output_path_for_bucket(output_root, bucket)
        expected_outputs[output_path] = rows
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rendered_rows = render_messages_json(rows)
        if output_path.exists() and output_path.read_text(encoding="utf-8") == rendered_rows:
            continue
        output_path.write_text(rendered_rows, encoding="utf-8")
        modified_paths.append(output_path)

    for prior_output in prior_outputs:
        if prior_output not in expected_outputs:
            prior_output.unlink()
            modified_paths.append(prior_output)

    verify_split_integrity(output_root, expected_outputs, deferred_messages, merged_messages)
    return sorted(modified_paths)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Merge WhatsApp scraper JSON exports by messageId, sort by time, and "
            "write weekly shards to YYYY-MM-DD/messages.json using podcast.py's "
            "week labels: Monday-Saturday rows go to the coming Sunday file, "
            "Sunday rows go to the following Sunday file, incomplete current/future "
            "weeks are skipped, and rows without a parseable ISO time go to "
            "unknown-time/messages.json."
        )
    )
    parser.add_argument("inputs", nargs="+", type=Path, help="Input JSON files to merge in order")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("."),
        help="Base directory where each week directory gets a messages.json shard",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    output_root = args.output_root.resolve()
    modified_paths = split_messages(args.inputs, output_root=output_root)
    for path in modified_paths:
        print(path.relative_to(output_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
