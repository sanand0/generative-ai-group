import json
import sys
import datetime as dt
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from split_whatsapp_messages import load_messages, main, merge_messages, split_messages


def test_merge_messages_uses_whatsapp_field_aware_rules():
    merged = merge_messages(
        [
            {
                "messageId": "img1",
                "userId": "group-1",
                "text": "short",
                "authorPhone": "123",
                "time": "2026-03-24T14:20:00.000Z",
                "mediaWidth": 320,
                "mediaDuration": "0:37",
                "reactions": "👍",
                "isRecalled": False,
            },
            {
                "messageId": "img1",
                "userId": "group-1",
                "text": "a much longer message body with more context",
                "time": "2026-03-24T14:20:30.000Z",
                "mediaWidth": 1080,
                "mediaDuration": "0:42",
                "reactions": "❤",
            },
        ]
    )

    assert merged == [
        {
            "messageId": "img1",
            "userId": "group-1",
            "text": "a much longer message body with more context",
            "authorPhone": "123",
            "time": "2026-03-24T14:20:30.000Z",
            "mediaWidth": 1080,
            "mediaDuration": "0:42",
            "reactions": "❤",
        }
    ]


def test_split_messages_merges_existing_week_file_first(tmp_path: Path):
    output_root = tmp_path
    week_dir = output_root / "2025-03-16"
    week_dir.mkdir()

    existing_rows = [
        {
            "messageId": "abc",
            "userId": "group-1",
            "time": "2025-03-10T01:00:00.000Z",
            "text": "short",
            "authorPhone": "111",
        },
        {
            "messageId": "older",
            "userId": "group-1",
            "time": "2025-03-15T00:30:00.000Z",
            "text": "keep me",
        },
    ]
    (week_dir / "messages.json").write_text(json.dumps(existing_rows), encoding="utf-8")

    input_path = tmp_path / "fresh.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "abc",
                    "userId": "group-1",
                    "time": "2025-03-10T01:00:30.000Z",
                    "text": "a much longer replacement body",
                    "reactions": "🔥",
                },
                {
                    "messageId": "newer",
                    "userId": "group-1",
                    "time": "2025-03-14T02:00:00.000Z",
                    "text": "new message",
                },
            ]
        ),
        encoding="utf-8",
    )

    split_messages([input_path], output_root=output_root, today=dt.date(2025, 3, 20))

    merged_rows = json.loads((output_root / "2025-03-16" / "messages.json").read_text(encoding="utf-8"))
    assert merged_rows == [
        {
            "messageId": "abc",
            "userId": "group-1",
            "time": "2025-03-10T01:00:30.000Z",
            "text": "a much longer replacement body",
            "authorPhone": "111",
            "reactions": "🔥",
        },
        {
            "messageId": "newer",
            "userId": "group-1",
            "time": "2025-03-14T02:00:00.000Z",
            "text": "new message",
        },
        {
            "messageId": "older",
            "userId": "group-1",
            "time": "2025-03-15T00:30:00.000Z",
            "text": "keep me",
        },
    ]


def test_load_messages_recovers_missing_opening_bracket(tmp_path: Path):
    input_path = tmp_path / "broken.json"
    input_path.write_text(
        """
  {
    "messageId": "abc",
    "userId": "group-1",
    "time": "2026-03-01T01:00:00.000Z"
  }
]
""".strip(),
        encoding="utf-8",
    )

    assert load_messages(input_path) == [
        {
            "messageId": "abc",
            "userId": "group-1",
            "time": "2026-03-01T01:00:00.000Z",
        }
    ]


def test_split_messages_preserves_rows_without_time(tmp_path: Path):
    input_path = tmp_path / "missing-time.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "no-time",
                    "userId": "group-1",
                    "text": "still keep this",
                },
                {
                    "messageId": "dated",
                    "userId": "group-1",
                    "time": "2026-03-01T01:00:00.000Z",
                    "text": "dated row",
                },
            ]
        ),
        encoding="utf-8",
    )

    split_messages([input_path], output_root=tmp_path, today=dt.date(2026, 3, 10))

    assert json.loads((tmp_path / "unknown-time" / "messages.json").read_text(encoding="utf-8")) == [
        {
            "messageId": "no-time",
            "userId": "group-1",
            "text": "still keep this",
        }
    ]


def test_split_messages_uses_podcast_week_boundaries(tmp_path: Path):
    input_path = tmp_path / "weekly.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "mon",
                    "userId": "group-1",
                    "time": "2025-03-10T09:00:00.000Z",
                    "text": "monday",
                },
                {
                    "messageId": "sat",
                    "userId": "group-1",
                    "time": "2025-03-15T09:00:00.000Z",
                    "text": "saturday",
                },
                {
                    "messageId": "sun",
                    "userId": "group-1",
                    "time": "2025-03-16T09:00:00.000Z",
                    "text": "sunday rolls forward",
                },
            ]
        ),
        encoding="utf-8",
    )

    split_messages([input_path], output_root=tmp_path, today=dt.date(2025, 3, 30))

    week_one = json.loads((tmp_path / "2025-03-16" / "messages.json").read_text(encoding="utf-8"))
    week_two = json.loads((tmp_path / "2025-03-23" / "messages.json").read_text(encoding="utf-8"))

    assert [row["messageId"] for row in week_one] == ["mon", "sat"]
    assert [row["messageId"] for row in week_two] == ["sun"]


def test_split_messages_skips_incomplete_current_week(tmp_path: Path):
    input_path = tmp_path / "current-week.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "not-yet",
                    "userId": "group-1",
                    "time": "2025-03-16T09:00:00.000Z",
                    "text": "wait until next sunday file is complete",
                }
            ]
        ),
        encoding="utf-8",
    )

    split_messages([input_path], output_root=tmp_path, today=dt.date(2025, 3, 22))

    assert not (tmp_path / "2025-03-23" / "messages.json").exists()


def test_split_messages_raises_if_written_output_loses_messages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    input_path = tmp_path / "weekly.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "mon",
                    "userId": "group-1",
                    "time": "2025-03-10T09:00:00.000Z",
                    "text": "monday",
                },
                {
                    "messageId": "sat",
                    "userId": "group-1",
                    "time": "2025-03-15T09:00:00.000Z",
                    "text": "saturday",
                },
            ]
        ),
        encoding="utf-8",
    )

    original_write_text = Path.write_text
    target_path = tmp_path / "2025-03-16" / "messages.json"

    def broken_write_text(self: Path, data: str, *args, **kwargs) -> int:
        if self == target_path:
            rows = json.loads(data)
            data = json.dumps(rows[:1], ensure_ascii=False, indent=2) + "\n"
        return original_write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", broken_write_text)

    with pytest.raises(ValueError, match="Lost messages"):
        split_messages([input_path], output_root=tmp_path, today=dt.date(2025, 3, 30))


def test_main_prints_only_modified_files_one_per_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    output_root = tmp_path / "out"
    input_path = tmp_path / "weekly.json"
    input_path.write_text(
        json.dumps(
            [
                {
                    "messageId": "week-one",
                    "userId": "group-1",
                    "time": "2025-03-10T09:00:00.000Z",
                    "text": "monday",
                },
                {
                    "messageId": "week-two",
                    "userId": "group-1",
                    "time": "2025-03-16T09:00:00.000Z",
                    "text": "sunday rolls forward",
                },
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["split_whatsapp_messages.py", str(input_path), "--output-root", str(output_root)],
    )

    assert main() == 0
    assert capsys.readouterr().out.splitlines() == [
        "2025-03-16/messages.json",
        "2025-03-23/messages.json",
    ]

    assert main() == 0
    assert capsys.readouterr().out == ""
