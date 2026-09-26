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


def test_process_week_generates_script_from_current_week_transcript(tmp_path: Path, monkeypatch):
    week = dt.date(2025, 3, 30)
    captured = {}

    def fake_get_podcast_script(messages_text, config, requested_week, previous_scripts=""):
        captured["messages_text"] = messages_text
        captured["week"] = requested_week
        captured["previous_scripts"] = previous_scripts
        return "Alex: New episode\n"

    monkeypatch.setattr(podcast, "get_podcast_script", fake_get_podcast_script)
    monkeypatch.setattr(podcast, "get_podcast_gemini", lambda *args, **kwargs: None)

    prior = week - dt.timedelta(days=7)
    prior_dir = tmp_path / str(prior)
    prior_dir.mkdir()
    (prior_dir / f"podcast-{prior}.md").write_text("Alex: Prior episode", encoding="utf-8")

    podcast.process_week(week, [make_item("abc")], {}, script_dir=tmp_path)

    assert captured["week"] == week
    assert "Prior episode" in captured["previous_scripts"]
    assert "Hello world" in captured["messages_text"]
    assert (tmp_path / str(week) / f"podcast-{week}.md").read_text() == "Alex: New episode\n"


def test_load_previous_scripts_uses_two_immediately_preceding_weeks(tmp_path: Path):
    week = dt.date(2026, 9, 20)
    for prior, text in [
        (dt.date(2026, 9, 6), "Alex: Two weeks ago."),
        (dt.date(2026, 9, 13), "Maya: Last week."),
    ]:
        d = tmp_path / str(prior)
        d.mkdir()
        (d / f"podcast-{prior}.md").write_text(text, encoding="utf-8")

    result = podcast.load_previous_scripts(tmp_path, week)

    assert "podcast-2026-09-06.md" in result
    assert "Two weeks ago" in result
    assert "podcast-2026-09-13.md" in result
    assert "Last week" in result


def test_fetch_link_contents_directly_extracts_and_caches_pages(tmp_path: Path, monkeypatch):
    calls = []

    class FakeResponse:
        text = "<html><body><main><h1>Useful article</h1><p>Important context.</p></main></body></html>"

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse()

    monkeypatch.setattr(podcast.httpx, "get", fake_get)
    monkeypatch.setattr(
        podcast.trafilatura,
        "extract",
        lambda html, **kwargs: "# Useful article\n\nImportant context.",
    )
    monkeypatch.setattr(podcast, "podcast_cache_dir", lambda: tmp_path)

    config = {"links": {"max_urls": 10, "max_chars": 3000, "timeout": 20}}
    text = "See https://example.com/article. Again https://example.com/article."

    first = podcast.fetch_link_contents(text, config)
    second = podcast.fetch_link_contents(text, config)

    assert first == second
    assert first.count("https://example.com/article") == 1
    assert "Important context" in first
    assert len(calls) == 1
    assert calls[0][1]["follow_redirects"] is True


def test_fetch_link_contents_skips_failed_pages(tmp_path: Path, monkeypatch):
    def fail(*args, **kwargs):
        raise podcast.httpx.HTTPError("blocked")

    monkeypatch.setattr(podcast.httpx, "get", fail)
    monkeypatch.setattr(podcast, "podcast_cache_dir", lambda: tmp_path)

    assert podcast.fetch_link_contents(
        "See https://example.com/blocked", {"links": {"max_urls": 10}}
    ) == ""


def test_format_and_parse_dialogue_preserve_optional_style_and_legacy_tags():
    turns = [
        {"speaker": "Alex", "text": "Welcome back!", "style": "excited"},
        {"speaker": "Maya", "text": "Normal delivery.", "style": ""},
    ]

    script = podcast.format_dialogue(turns)
    assert script == "Alex: [style: excited] Welcome back!\nMaya: Normal delivery.\n"
    assert podcast.parse_dialogue(script, ["Alex", "Maya"]) == turns

    legacy = podcast.parse_dialogue(
        "Alex: [excited] Welcome back!\nMaya: [laughs] Nice. [short pause] Next.",
        ["Alex", "Maya"],
    )
    assert legacy == [
        {"speaker": "Alex", "text": "Welcome back!", "style": "excited"},
        {"speaker": "Maya", "text": "<laugh> Nice. <short pause> Next.", "style": ""},
    ]


def test_format_dialogue_adds_blank_line_at_section_boundary():
    turns = [
        {"speaker": "Alex", "text": "First.", "style": "", "new_section": False},
        {"speaker": "Maya", "text": "Still first.", "style": "", "new_section": False},
        {"speaker": "Alex", "text": "New topic.", "style": "", "new_section": True},
    ]
    assert podcast.format_dialogue(turns) == (
        "Alex: First.\nMaya: Still first.\n\nAlex: New topic.\n"
    )


def test_get_podcast_script_uses_luna_structured_output(monkeypatch, tmp_path):
    captured = {}

    class FakeResponse:
        output_text = json.dumps(
            {
                "turns": [
                    {"speaker": "Alex", "text": "Hello.", "style": ""},
                    {"speaker": "Maya", "text": "Hi.", "style": ""},
                ]
            }
        )

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.responses = FakeResponses()

    monkeypatch.setattr(podcast, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(podcast, "api_key", lambda *_: "test-key")
    monkeypatch.setattr(podcast, "podcast_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(
        podcast,
        "fetch_link_contents",
        lambda *_: "## https://example.com\nFetched page context.",
    )

    config = {
        "podcast": "Week $WEEK; target $TARGET_WORDS words.",
        "openai": {"model": "gpt-6-luna"},
    }
    script = podcast.get_podcast_script(
        "one two three https://example.com",
        config,
        dt.date(2026, 9, 20),
        "Alex: Previous episode.",
    )

    assert script == "Alex: Hello.\nMaya: Hi.\n"
    assert captured["model"] == "gpt-6-luna"
    assert "reasoning" not in captured
    assert captured["text"]["format"] == podcast.DIALOGUE_FORMAT
    assert "20 September 2026" in captured["input"][0]["content"]
    user_content = captured["input"][1]["content"]
    assert "CURRENT WEEK TRANSCRIPT — PRIMARY SOURCE" in user_content
    assert "Fetched page context" in user_content
    assert "PREVIOUS EPISODES — CONTEXT ONLY" in user_content
    assert "Previous episode" in user_content


def test_build_speech_content_adds_style_only_when_present():
    content = podcast.build_speech_content(
        [
            {"speaker": "Alex", "text": "One", "style": "quietly amused"},
            {"speaker": "Maya", "text": "Two", "style": ""},
        ]
    )

    assert content[0]["annotations"][0] == {
        "type": "speech_metadata",
        "speaker": "Alex",
        "style": "quietly amused",
    }
    assert content[1]["annotations"][0] == {
        "type": "speech_metadata",
        "speaker": "Maya",
    }


def test_main_tts_script_dry_run_chunks_dialogue(tmp_path: Path, monkeypatch, capsys):
    script_path = tmp_path / "sample-dialogue.md"
    script_path.write_text(
        "Alex: [style: excited] Welcome back.\nMaya: <laugh> Two stories today.\n",
        encoding="utf-8",
    )
    config = {
        "gemini": {
            "model": "gemini-3.8-flash-lite-tts",
            "chunk_size": 10,
            "sample_rate": 24000,
            "speakers": [
                {"name": "Alex", "voice_name": "Algieba"},
                {"name": "Maya", "voice_name": "Kore"},
            ],
        }
    }
    monkeypatch.setattr(podcast, "load_config", lambda _script_dir: config)

    assert podcast.main(
        ["tts-script", "--script-file", str(script_path), "--dry-run"],
        script_dir=tmp_path,
    ) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "dry-run"
    assert result["model"] == "gemini-3.8-flash-lite-tts"
    assert result["turn_count"] == 2
    assert result["chunk_count"] == 1
    assert result["speaker_names"] == ["Alex", "Maya"]


def test_main_describe_returns_machine_readable_schema(tmp_path: Path, capsys):
    assert podcast.main(["--describe"], script_dir=tmp_path) == 0
    result = json.loads(capsys.readouterr().out)
    assert sorted(result["commands"]) == ["tts-script", "weekly"]
