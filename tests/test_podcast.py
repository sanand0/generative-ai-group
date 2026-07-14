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


def test_process_week_passes_only_the_previous_two_weeks_as_context(tmp_path: Path, monkeypatch):
    week = dt.date(2025, 3, 30)
    for prior_week, script in [
        (dt.date(2025, 3, 9), "Alex: Three weeks ago"),
        (dt.date(2025, 3, 16), "Alex: Two weeks ago"),
        (dt.date(2025, 3, 23), "Maya: Last week"),
    ]:
        prior_dir = tmp_path / str(prior_week)
        prior_dir.mkdir()
        (prior_dir / f"podcast-{prior_week}.md").write_text(script, encoding="utf-8")

    captured = {}

    def fake_get_podcast_script(messages_text, config, requested_week, previous_scripts):
        captured["messages_text"] = messages_text
        captured["week"] = requested_week
        captured["previous_scripts"] = previous_scripts
        return 0.0, "Alex: New episode"

    monkeypatch.setattr(podcast, "get_podcast_script", fake_get_podcast_script)
    monkeypatch.setattr(podcast, "get_podcast_gemini", lambda *args, **kwargs: None)

    podcast.process_week(week, [make_item("abc")], {}, script_dir=tmp_path)

    assert captured["week"] == week
    assert "Hello world" in captured["messages_text"]
    assert "podcast-2025-03-16.md" in captured["previous_scripts"]
    assert "Two weeks ago" in captured["previous_scripts"]
    assert "podcast-2025-03-23.md" in captured["previous_scripts"]
    assert "Last week" in captured["previous_scripts"]
    assert "Three weeks ago" not in captured["previous_scripts"]


def test_get_podcast_script_labels_previous_scripts_as_continuity_only(monkeypatch):
    class FakeResponse:
        text = ""

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            return {
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "output": [{"content": [{"text": "Alex: Fresh episode"}]}],
            }

    captured = {}

    def fake_post(*args, **kwargs):
        captured["payload"] = kwargs["json"]
        return FakeResponse()

    monkeypatch.setattr(podcast.requests, "post", fake_post)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("JINA_API_KEY", "test-key")

    podcast.get_podcast_script(
        "- Alice: This week's new discussion",
        {"podcast": "Prompt for $WEEK"},
        dt.date(2025, 3, 30),
        "## podcast-2025-03-23.md\nAlex: An earlier discussion",
    )

    user_content = captured["payload"]["input"][1]["content"]
    assert "CURRENT WEEK TRANSCRIPT" in user_content
    assert "PREVIOUS EPISODES — CONTEXT ONLY" in user_content
    assert "This week's new discussion" in user_content
    assert "An earlier discussion" in user_content
    assert "Do not repeat or recap" in user_content


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
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("JINA_API_KEY", "test-key")

    with pytest.raises(FakeHTTPError):
        podcast.get_podcast_script(
            "Threaded messages",
            {"podcast": "Prompt for $WEEK"},
            dt.date(2025, 3, 16),
        )

    assert capsys.readouterr().err == '{"error":{"message":"Bad request"}}\n'


def test_build_gemini_request_uses_new_model_and_single_speaker_payload():
    config = make_gemini_config()

    segments, normalized_script, speakers = podcast.split_script_segments(
        "Alex: [excited] Welcome back!\nMaya: Good to be here.\nAnd we have updates.",
        config,
    )

    assert normalized_script == (
        "Alex: [excited] Welcome back!\nMaya: Good to be here. And we have updates."
    )
    assert [speaker.name for speaker in speakers] == ["Alex", "Maya"]

    payload = podcast.build_gemini_request(segments[0][1], segments[0][0], config)

    assert payload["model"] == "gemini-3.1-flash-tts-preview"
    assert payload["generationConfig"]["speechConfig"]["voiceConfig"] == {
        "prebuiltVoiceConfig": {"voiceName": "Algieba"}
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
