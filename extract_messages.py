#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///

import json
import subprocess
from pathlib import Path


def extract_messages() -> list[dict]:
    """Read the local WhatsApp archive in the format used by the podcast."""
    command = ["wacli", "--read-only", "messages", "list", "--json", "--chat", "120363049558306142@g.us", "--limit", "10000"]
    messages = []
    cursor = None
    while True:
        result = json.loads(subprocess.check_output(command + (["--cursor", cursor] if cursor else []), text=True))
        if not result["success"]:
            raise RuntimeError(result["error"])
        data = result["data"]
        for row in data["messages"]:
            message = {
                "messageId": row["MsgID"],
                "time": row["Timestamp"],
                "author": row["SenderName"] or row["SenderJID"].split("@")[0],
                "text": row["Text"],
            }
            if row.get("quoted_msg_id"):
                message["quoteMessageId"] = row["quoted_msg_id"]
            messages.append(message)
        if not data["page"]["has_more"]:
            break
        cursor = data["page"]["next_cursor"]
        if not cursor:
            raise ValueError("WhatsApp archive returned an incomplete page without a cursor")
    return sorted(messages, key=lambda message: (message["time"], message["messageId"]))


if __name__ == "__main__":
    messages = extract_messages()
    if not messages:
        raise ValueError("No messages found in the WhatsApp archive")
    Path("messages.json").write_text(json.dumps(messages, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(messages)} messages to messages.json", flush=True)
