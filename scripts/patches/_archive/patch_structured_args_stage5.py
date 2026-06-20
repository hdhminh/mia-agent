#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def replace_or_fail(code: str, old: str, new: str, *, label: str) -> str:
    if old not in code:
        raise ValueError(f"missing pattern for {label}: {old[:120]!r}")
    return code.replace(old, new, 1)


def patch_node(path: Path, node_name: str, transform) -> None:
    workflow = json.loads(path.read_text())
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            code = node["parameters"]["jsCode"]
            node["parameters"]["jsCode"] = transform(code)
            path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
            print(f"patched {path.name}:{node_name}")
            return
    raise ValueError(f"node {node_name!r} not found in {path}")


def patch_gateway_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        """  'gmail.send_email': {\n    workflowKey: 'gmail.send_email',\n    build: (a) => ({\n      text:\n        clean(a.instruction) ||\n        [clean(a.to || a.toEmail), clean(a.subject)].filter(Boolean).join(' ') ||\n        'gửi email',\n      to: clean(a.to || a.toEmail),\n      toEmail: clean(a.toEmail || a.to),\n      subject: clean(a.subject),\n      body: clean(a.body),\n    }),\n  },""",
        """  'gmail.send_email': {\n    workflowKey: 'gmail.send_email',\n    build: (a) => ({\n      text:\n        clean(a.instruction) ||\n        [clean(a.to || a.toEmail), clean(a.subject)].filter(Boolean).join(' ') ||\n        'gửi email',\n      to: clean(a.to || a.toEmail),\n      toEmail: clean(a.toEmail || a.to),\n      subject: clean(a.subject),\n      body: clean(a.body),\n      cc: clean(a.cc),\n      bcc: clean(a.bcc),\n    }),\n  },""",
        label="gateway gmail.send_email",
    )
    return code


def patch_calendar_find_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="calendar_find args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || source.query || args.query || message.text || payload.text || '').trim();",
        label="calendar_find raw",
    )
    code = replace_or_fail(
        code,
        "const text = normalize(source.text || raw);",
        "const text = normalize(source.text || source.query || args.query || raw);",
        label="calendar_find text",
    )
    code = replace_or_fail(
        code,
        "const calendarId = source.calendarId || payload.calendarId || 'primary';",
        "const calendarId = source.calendarId || args.calendarId || payload.calendarId || 'primary';",
        label="calendar_find calendarId",
    )
    code = replace_or_fail(
        code,
        "let afterDate = now;\nlet beforeDate = new Date(now.getTime() + 1000 * 60 * 60 * 24 * 30);",
        "const explicitDateFrom = String(source.dateFrom || args.dateFrom || '').trim();\nconst explicitDateTo = String(source.dateTo || args.dateTo || '').trim();\nlet afterDate = explicitDateFrom ? new Date(explicitDateFrom) : now;\nlet beforeDate = explicitDateTo ? new Date(explicitDateTo) : new Date(now.getTime() + 1000 * 60 * 60 * 24 * 30);",
        label="calendar_find explicit dates",
    )
    code = replace_or_fail(
        code,
        "if (/cuoi tuan nay/.test(text)) {",
        "if (explicitDateFrom || explicitDateTo) {\n  // structured date filters already provided\n} else if (/cuoi tuan nay/.test(text)) {",
        label="calendar_find bypass date parse",
    )
    code = replace_or_fail(
        code,
        "const query = raw\n  .replace(/^(tim lich|tim su kien|search event|find event|xem lich voi|lich)\\s*/i, '')\n  .replace(/\\b(hom nay|ngay mai|mai|tuan sau|tuan nay|cuoi tuan nay|cuoi tuan sau|thu\\s*[2-7]|chu nhat)\\b/gi, '')\n  .replace(/\\s+/g, ' ')\n  .trim();",
        "const explicitQuery = String(source.query || args.query || '').trim();\nconst query = (explicitQuery || raw)\n  .replace(/^(tim lich|tim su kien|search event|find event|xem lich voi|lich)\\s*/i, '')\n  .replace(/\\b(hom nay|ngay mai|mai|tuan sau|tuan nay|cuoi tuan nay|cuoi tuan sau|thu\\s*[2-7]|chu nhat)\\b/gi, '')\n  .replace(/\\s+/g, ' ')\n  .trim();",
        label="calendar_find query",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, payload, message, rawText: raw, text, chatId, calendarId, query, after: iso(afterDate), before: iso(beforeDate, 23, 59, true) } }];",
        "return [{ json: { ...source, payload, message, rawText: raw, text, chatId, calendarId, query, limit: Number(source.limit || args.limit || 5) || 5, after: explicitDateFrom || iso(afterDate), before: explicitDateTo || iso(beforeDate, 23, 59, true) } }];",
        label="calendar_find return",
    )
    return code


def patch_gmail_send_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="gmail_send args",
    )
    code = replace_or_fail(
        code,
        "const structuredTo = String(source.toEmail || source.to || payload.toEmail || payload.to || '').trim();\nconst structuredSubject = String(source.subject || payload.subject || '').trim();\nconst structuredBody = String(source.body || payload.body || '').trim();",
        "const structuredTo = String(source.toEmail || source.to || args.toEmail || args.to || payload.toEmail || payload.to || '').trim();\nconst structuredSubject = String(source.subject || args.subject || payload.subject || '').trim();\nconst structuredBody = String(source.body || args.body || payload.body || '').trim();\nconst structuredCc = String(source.cc || args.cc || payload.cc || '').trim();\nconst structuredBcc = String(source.bcc || args.bcc || payload.bcc || '').trim();",
        label="gmail_send structured fields",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, payload, message, chatId, toEmail, subject, body, isReady, isDraftSend, response: isReady ? '' : guidance } }];",
        "return [{ json: { ...source, payload, message, chatId, toEmail, subject, body, cc: structuredCc, bcc: structuredBcc, isReady, isDraftSend, response: isReady ? '' : guidance } }];",
        label="gmail_send return",
    )
    return code


def main() -> None:
    patch_node(ROOT / "workflows/core/workflow_mia_tool_gateway.json", "Prepare Tool Request", patch_gateway_prepare)
    patch_node(ROOT / "google/calendar/workflow_sub_google_calendar_find_event.json", "Chuan Bi Tim Lich", patch_calendar_find_prepare)
    patch_node(ROOT / "google/gmail/workflow_sub_google_gmail_send_email.json", "Parse Gui Email", patch_gmail_send_prepare)


if __name__ == "__main__":
    main()
