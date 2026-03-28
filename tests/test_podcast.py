import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import podcast


def make_item(
    message_id: str,
    *,
    time: str = "2025-03-10T09:00:00.000Z",
    text: str = "Hello world",
    author: str = "Alice",
) -> dict:
    return {
        "messageId": message_id,
        "time": time,
        "text": text,
        "author": author,
        "dt": dt.datetime.fromisoformat(time.replace("Z", "+00:00")),
    }


def test_process_week_writes_messages_json_next_to_messages_txt(tmp_path: Path, monkeypatch):
    week = dt.date(2025, 3, 16)
    week_dir = tmp_path / str(week)
    week_dir.mkdir()
    (week_dir / f"podcast-{week}.md").write_text("Host: existing script", encoding="utf-8")
    (week_dir / f"podcast-{week}.mp3").write_bytes(b"existing audio")

    monkeypatch.setattr(
        podcast,
        "get_podcast_script",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM call not expected")),
    )
    monkeypatch.setattr(
        podcast,
        "get_podcast_gemini",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("TTS call not expected")),
    )

    item = make_item("abc", text="Hello weekly structure")
    podcast.process_week(week, [item], {}, script_dir=tmp_path)

    assert json.loads((week_dir / "messages.json").read_text(encoding="utf-8")) == [
        {
            "messageId": "abc",
            "time": "2025-03-10T09:00:00.000Z",
            "text": "Hello weekly structure",
            "author": "Alice",
        }
    ]
    assert (week_dir / "messages.txt").read_text(encoding="utf-8").strip() == "- Alice: Hello weekly structure"


def test_main_dry_run_verifies_without_writing_or_api_calls(tmp_path: Path, monkeypatch):
    (tmp_path / "config.toml").write_text('podcast = "Test prompt for $WEEK"\n', encoding="utf-8")
    (tmp_path / "gen-ai-messages.json").write_text(
        json.dumps(
            [
                {
                    "messageId": "abc",
                    "time": "2025-03-10T09:00:00.000Z",
                    "text": "Hello weekly structure",
                    "author": "Alice",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        podcast,
        "get_podcast_script",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM call not expected")),
    )
    monkeypatch.setattr(
        podcast,
        "get_podcast_gemini",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("TTS call not expected")),
    )

    assert podcast.main(["--dry-run"], script_dir=tmp_path) == 0
    assert not (tmp_path / "2025-03-16" / "messages.json").exists()
    assert not (tmp_path / "2025-03-16" / "messages.txt").exists()
    assert not (tmp_path / "podcast.xml").exists()


def test_main_dry_run_uses_existing_week_messages_json(tmp_path: Path, monkeypatch):
    week_dir = tmp_path / "2025-03-16"
    week_dir.mkdir()
    (tmp_path / "config.toml").write_text('podcast = "Test prompt for $WEEK"\n', encoding="utf-8")
    (week_dir / "messages.json").write_text(
        json.dumps(
            [
                {
                    "messageId": "abc",
                    "time": "2025-03-10T09:00:00.000Z",
                    "text": "Hello weekly structure",
                    "author": "Alice",
                }
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        podcast,
        "get_podcast_script",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("LLM call not expected")),
    )
    monkeypatch.setattr(
        podcast,
        "get_podcast_gemini",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("TTS call not expected")),
    )

    assert podcast.main(["--dry-run"], script_dir=tmp_path) == 0
    assert not (week_dir / "messages.txt").exists()
    assert not (tmp_path / "podcast.xml").exists()
