#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TOOL_URL = "http://127.0.0.1:5678/webhook/mia-tool"
CHAT_URL = "http://127.0.0.1:8000/mia/chat"


def read_env(key: str) -> str:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def run_tool(tool: str, args: dict[str, Any], text: str) -> dict[str, Any]:
    token = read_env("MIA_TOOL_GATEWAY_TOKEN")
    payload = {
        "tool": tool,
        "args": args,
        "chatId": "codex-safe-smoke",
        "requestId": str(uuid.uuid4()),
        "deliveryMode": "return",
        "text": text,
        "rawText": text,
    }
    headers = {"x-mia-tool-token": token} if token else {}
    return post_json(TOOL_URL, payload, headers)


def run_chat(text: str) -> dict[str, Any]:
    token = read_env("MIA_CORE_API_TOKEN")
    return post_json(
        CHAT_URL,
        {
            "chat_id": "codex-safe-smoke",
            "text": text,
            "metadata": {"source": "safe-smoke"},
        },
        {"x-mia-core-token": token} if token else {},
    )


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_tool_case(name: str, tool: str, args: dict[str, Any], text: str, expected_ok: bool | None) -> None:
    try:
        data = run_tool(tool, args, text)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise AssertionError(f"{name}: HTTP {exc.code} {body[:500]}") from exc

    final_text = str(data.get("text") or "").strip()
    assert_true(final_text != "", f"{name}: empty text")
    if expected_ok is not None:
        assert_true(bool(data.get("ok")) == expected_ok, f"{name}: expected ok={expected_ok}, got {data.get('ok')}")
    links = data.get("links") or []
    assert_true(isinstance(links, list), f"{name}: links is not a list")
    assert_true(len(links) <= 3, f"{name}: too many links ({len(links)})")
    print(f"ok tool {name}: ok={data.get('ok')} text={final_text[:120].replace(chr(10), ' | ')}")


def check_chat_case(name: str, text: str, expected_tool: str) -> None:
    data = run_chat(text)
    final_text = str(data.get("final_text") or "").strip()
    tools = data.get("tools_called") or []
    assert_true(final_text != "", f"{name}: empty final_text")
    assert_true(expected_tool in tools, f"{name}: expected {expected_tool}, got {tools}")
    assert_true(final_text.count("http://") + final_text.count("https://") <= 3, f"{name}: too many visible links")
    print(f"ok chat {name}: tools={tools} text={final_text[:120].replace(chr(10), ' | ')}")


def main() -> int:
    checks: list[tuple[str, str, dict[str, Any], str, bool | None]] = [
        ("calendar_create_missing", "calendar.create_event", {}, "tạo lịch", False),
        ("gmail_send_missing", "gmail.send_email", {}, "gửi mail", False),
        (
            "gmail_reply_requires_message_id",
            "gmail.reply_email",
            {"searchQuery": "definitely-no-mail-xyz", "body": "ok"},
            "trả lời mail definitely-no-mail-xyz nội dung ok",
            False,
        ),
        (
            "docs_append_not_found",
            "docs.append_doc",
            {"docName": "definitely-no-doc-xyz", "content": "abc"},
            "thêm vào doc definitely-no-doc-xyz: abc",
            False,
        ),
        (
            "drive_info_not_found",
            "drive.get_file_info",
            {"fileName": "definitely-no-file-xyz"},
            "thông tin file definitely-no-file-xyz",
            False,
        ),
        (
            "sheets_update_not_found",
            "sheets.update_cell",
            {"sheetName": "definitely-no-sheet-xyz", "cell": "B2", "value": "x"},
            "cập nhật sheet definitely-no-sheet-xyz ô B2 thành x",
            False,
        ),
    ]

    for case in checks:
        check_tool_case(*case)

    chat_checks = [
        ("gold_direct", "giá vàng hôm nay", "gold_get_price"),
        ("weather_direct", "thời tiết Hà Nội", "weather_get"),
    ]
    for case in chat_checks:
        check_chat_case(*case)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - smoke script should surface concise failure.
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
