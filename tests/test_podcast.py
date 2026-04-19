import datetime as dt
import json
import sys
from pathlib import Path

import pytest

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


def make_gemini_config() -> dict:
    return {
        "podcast_style": "Podcast style: Warm and lively.",
        "gemini": {
            "model": "gemini-3.1-flash-tts-preview",
            "ffmpeg_command": ["ffmpeg", "-i", "{pcm}", "{output}"],
            "speakers": [
                {
                    "name": "Alex",
                    "voice_name": "Algieba",
                    "profile": "Energetic, curious, and upbeat.",
                },
                {
                    "name": "Maya",
                    "voice_name": "Kore",
                    "profile": "Warm, clear, and grounded.",
                },
            ],
        },
    }


def test_process_week_writes_messages_json_next_to_messages_txt(tmp_path: Path, monkeypatch):
    week = dt.date(2025, 3, 16)
    week_dir = tmp_path / str(week)
    week_dir.mkdir()
    (week_dir / f"podcast-{week}.md").write_text("Alex: existing script", encoding="utf-8")
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


def test_get_podcast_script_prints_api_error_body(monkeypatch, capsys: pytest.CaptureFixture[str]):
    class FakeHTTPError(Exception):
        pass

    class FakeResponse:
        text = '{"error":{"message":"Bad request"}}'

        def raise_for_status(self) -> None:
            raise FakeHTTPError("400 Client Error")

    monkeypatch.setattr(podcast.requests, "post", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(FakeHTTPError):
        podcast.get_podcast_script(
            "Threaded messages",
            {"podcast": "Prompt for $WEEK"},
            dt.date(2025, 3, 16),
        )

    assert capsys.readouterr().err == '{"error":{"message":"Bad request"}}\n'


def test_build_gemini_request_uses_new_model_and_multispeaker_payload():
    config = make_gemini_config()

    payload, normalized_script, speakers = podcast.build_gemini_request(
        "Alex: [excited] Welcome back!\nMaya: Good to be here.\nAnd we have updates.",
        config,
    )

    assert payload["model"] == "gemini-3.1-flash-tts-preview"
    assert normalized_script == (
        "Alex: [excited] Welcome back!\nMaya: Good to be here. And we have updates."
    )
    assert [speaker.name for speaker in speakers] == ["Alex", "Maya"]
    assert payload["generationConfig"]["speechConfig"]["multiSpeakerVoiceConfig"] == {
        "speakerVoiceConfigs": [
            {
                "speaker": "Alex",
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Algieba"}},
            },
            {
                "speaker": "Maya",
                "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}},
            },
        ]
    }
    prompt_text = payload["contents"][0]["parts"][0]["text"]
    assert "TRANSCRIPT" in prompt_text
    assert "[excited]" in prompt_text


def test_main_tts_script_dry_run_validates_script_and_derives_output(
    tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
):
    script_path = tmp_path / "sample-dialogue.md"
    script_path.write_text(
        "Alex: [excited] Welcome back.\nMaya: [laughs] We have two quick stories today.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(podcast, "load_config", lambda _script_dir: make_gemini_config())

    assert podcast.main(["tts-script", "--script-file", str(script_path), "--dry-run"], script_dir=tmp_path) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["command"] == "tts-script"
    assert result["status"] == "dry-run"
    assert result["speaker_names"] == ["Alex", "Maya"]
    assert result["audio_path"].endswith("sample-dialogue.mp3")


def test_main_describe_returns_machine_readable_schema(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    assert podcast.main(["--describe"], script_dir=tmp_path) == 0
    result = json.loads(capsys.readouterr().out)
    assert sorted(result["commands"]) == ["tts-script", "weekly"]
