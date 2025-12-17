import json
from pathlib import Path

import whatsapp_analysis as wa


def sample_messages():
    return [
        {
            "messageId": "1",
            "author": "Alice",
            "text": "Hello team! Please review https://example.com",
            "time": "2025-01-01T10:00:00Z",
            "quoteAuthor": None,
            "isSystemMessage": False,
        },
        {
            "messageId": "2",
            "author": "Bob",
            "text": "Thanks Alice!",
            "time": "2025-01-01T10:05:00Z",
            "quoteAuthor": "Alice",
            "isSystemMessage": False,
        },
        {
            "messageId": "3",
            "author": "Alice",
            "text": "Any questions?",
            "time": "2025-01-01T11:00:00Z",
            "quoteAuthor": None,
            "isSystemMessage": False,
        },
    ]


def test_generate_report_has_all_analyses(tmp_path: Path):
    fixture = tmp_path / "chat.json"
    fixture.write_text(json.dumps(sample_messages()), encoding="utf-8")
    messages = wa.load_messages(fixture)
    report = wa.generate_report(messages)
    assert report.count("### ") == 85
    assert "Authors & Participation" in report
    assert "Topics & Semantics" in report


def test_ensure_lines_minimum():
    lines = wa.ensure_lines(["- one"], "Test")
    assert len(lines) >= 3
    assert lines[0].startswith("-")


def test_report_line_limits():
    report = wa.generate_report(sample_messages())
    for section in report.split("### ")[1:]:
        lines = section.split("\n")[1:]
        assert len(lines) <= 20
        assert all(len(line) <= 100 for line in lines)
