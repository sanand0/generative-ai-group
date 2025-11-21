import json
from pathlib import Path

import pytest

from analysis.whatsapp_analysis import ANALYSIS_SPEC, generate_report, parse_messages


@pytest.fixture()
def sample_messages_path(tmp_path: Path) -> Path:
    fixture = [
        {
            "messageId": "1",
            "author": "Ada",
            "authorPhone": "123",
            "isSystemMessage": False,
            "text": "Hello team!",
            "time": "2024-01-01T00:00:00.000Z",
        },
        {
            "messageId": "2",
            "author": "Ben",
            "authorPhone": "456",
            "isSystemMessage": False,
            "quoteAuthor": "Ada",
            "quoteText": "Hello team!",
            "text": "?",
            "time": "2024-01-01T01:00:00.000Z",
        },
        {
            "messageId": "3",
            "author": "Ada",
            "authorPhone": "123",
            "isSystemMessage": False,
            "text": "Thanks Ben",
            "time": "2024-01-02T00:00:00.000Z",
        },
    ]
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def test_report_contains_all_titles(sample_messages_path: Path) -> None:
    messages = parse_messages(sample_messages_path)
    output = generate_report(messages)
    for category, items in ANALYSIS_SPEC.items():
        assert category in output
        for name in items:
            assert name in output


def test_output_has_short_lines(sample_messages_path: Path) -> None:
    messages = parse_messages(sample_messages_path)
    lines = generate_report(messages).splitlines()
    assert all(len(line) <= 100 for line in lines if line.strip())


def test_parses_reference_file() -> None:
    path = Path(__file__).resolve().parent.parent / "gen-ai-messages.json"
    messages = parse_messages(path)
    output = generate_report(messages)
    assert output.count("**") >= len(ANALYSIS_SPEC)
    assert "Authors & Participation" in output
