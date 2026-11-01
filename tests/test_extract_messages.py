import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch

from extract_messages import extract_messages


def test_extract_messages_pages_and_maps_workflow_fields():
    pages = [
        {"success": True, "data": {"messages": [
            {"MsgID": "reply", "Timestamp": "2026-10-31T01:02:03Z", "SenderJID": "123@s.whatsapp.net", "SenderName": "", "Text": "Reply", "quoted_msg_id": "original"},
        ], "page": {"has_more": True, "next_cursor": "next"}}},
        {"success": True, "data": {"messages": [
            {"MsgID": "original", "Timestamp": "2026-10-30T01:00:00Z", "SenderJID": "456@s.whatsapp.net", "SenderName": "A", "Text": "Hello"},
        ], "page": {"has_more": False}}},
    ]
    with patch("extract_messages.subprocess.check_output", side_effect=[json.dumps(page) for page in pages]) as call:
        messages = extract_messages()
    assert messages == [
        {"messageId": "original", "time": "2026-10-30T01:00:00Z", "author": "A", "text": "Hello"},
        {"messageId": "reply", "time": "2026-10-31T01:02:03Z", "author": "123", "text": "Reply", "quoteMessageId": "original"},
    ]
    assert call.call_args_list[1].args[0][-2:] == ["--cursor", "next"]
