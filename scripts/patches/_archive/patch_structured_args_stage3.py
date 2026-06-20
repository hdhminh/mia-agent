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
        """  'calendar.delete_event': {\n    workflowKey: 'calendar.delete_event',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.eventId) ? `xóa lịch ${clean(a.eventId)}` : 'xóa lịch'),\n      eventId: clean(a.eventId),\n      query: clean(a.query),\n    }),\n  },""",
        """  'calendar.delete_event': {\n    workflowKey: 'calendar.delete_event',\n    build: (a) => ({\n      text:\n        clean(a.instruction) ||\n        (clean(a.query) ? `xóa lịch ${clean(a.query)}` : clean(a.eventId) ? `xóa lịch ${clean(a.eventId)}` : 'xóa lịch'),\n      eventId: clean(a.eventId),\n      query: clean(a.query),\n      calendarId: clean(a.calendarId),\n    }),\n  },""",
        label="gateway calendar.delete_event",
    )
    code = replace_or_fail(
        code,
        """  'calendar.check_availability': {\n    workflowKey: 'calendar.check_availability',\n    build: (a) => ({\n      text: clean(a.instruction) || 'kiểm tra lịch rảnh',\n      date: clean(a.date),\n      dateFrom: clean(a.dateFrom),\n      dateTo: clean(a.dateTo),\n      timezone: clean(a.timezone),\n    }),\n  },""",
        """  'calendar.check_availability': {\n    workflowKey: 'calendar.check_availability',\n    build: (a) => ({\n      text: clean(a.instruction) || 'kiểm tra lịch rảnh',\n      date: clean(a.date),\n      dateFrom: clean(a.dateFrom),\n      dateTo: clean(a.dateTo),\n      startAt: clean(a.startAt),\n      endAt: clean(a.endAt),\n      timezone: clean(a.timezone),\n      calendarId: clean(a.calendarId),\n    }),\n  },""",
        label="gateway calendar.check_availability",
    )
    code = replace_or_fail(
        code,
        """  'gmail.read_email': {\n    workflowKey: 'gmail.read_email',\n    build: (a) => ({ text: clean(a.instruction) || 'đọc email', messageId: clean(a.messageId) }),\n  },""",
        """  'gmail.read_email': {\n    workflowKey: 'gmail.read_email',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.query) ? `đọc email ${clean(a.query)}` : 'đọc email'),\n      query: clean(a.query),\n      messageId: clean(a.messageId),\n    }),\n  },""",
        label="gateway gmail.read_email",
    )
    code = replace_or_fail(
        code,
        """  'gmail.draft_email': {\n    workflowKey: 'gmail.draft_email',\n    build: (a) => ({\n      text: clean(a.instruction) || 'soạn email',\n      to: clean(a.to || a.toEmail),\n      toEmail: clean(a.toEmail || a.to),\n      subject: clean(a.subject),\n      body: clean(a.body),\n    }),\n  },""",
        """  'gmail.draft_email': {\n    workflowKey: 'gmail.draft_email',\n    build: (a) => ({\n      text:\n        clean(a.instruction) ||\n        [clean(a.to || a.toEmail), clean(a.subject)].filter(Boolean).join(' ') ||\n        'soạn email',\n      to: clean(a.to || a.toEmail),\n      toEmail: clean(a.toEmail || a.to),\n      subject: clean(a.subject),\n      body: clean(a.body),\n    }),\n  },""",
        label="gateway gmail.draft_email",
    )
    code = replace_or_fail(
        code,
        """  'gmail.reply_email': {\n    workflowKey: 'gmail.reply_email',\n    build: (a) => ({\n      text: clean(a.instruction) || 'trả lời email',\n      messageId: clean(a.messageId),\n      body: clean(a.body),\n    }),\n  },""",
        """  'gmail.reply_email': {\n    workflowKey: 'gmail.reply_email',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.searchQuery) ? `trả lời email ${clean(a.searchQuery)}` : 'trả lời email'),\n      messageId: clean(a.messageId),\n      searchQuery: clean(a.searchQuery),\n      body: clean(a.body),\n    }),\n  },""",
        label="gateway gmail.reply_email",
    )
    return code


def patch_calendar_delete_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="calendar_delete args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || source.query || args.query || args.eventId || message.text || payload.text || '').trim();",
        label="calendar_delete raw",
    )
    code = replace_or_fail(
        code,
        "const calendarId = source.calendarId || payload.calendarId || 'primary';",
        "const calendarId = source.calendarId || args.calendarId || payload.calendarId || 'primary';",
        label="calendar_delete calendarId",
    )
    code = replace_or_fail(
        code,
        "const text = normalize(source.text || raw);",
        "const text = normalize(source.text || source.query || args.query || raw);\nconst directEventId = String(source.eventId || args.eventId || '').trim();",
        label="calendar_delete text/directEventId",
    )
    code = replace_or_fail(
        code,
        "const query = raw\n  .replace(/^(xoa lich|xóa lịch|huy lich|huỷ lịch|hủy lịch|xoa su kien|xóa sự kiện|huy su kien|hủy sự kiện|delete event|cancel event)\\s*/i, '')\n  .replace(/\\b(hom nay|ngay mai|mai|ngay kia|tuan sau|tuan nay|cuoi tuan nay|cuoi tuan sau|thu\\s*[2-7]|chu nhat)\\b/gi, '')\n  .replace(/\\s+/g, ' ')\n  .trim();",
        "const explicitQuery = String(source.query || args.query || '').trim();\nconst query = (explicitQuery || raw)\n  .replace(/^(xoa lich|xóa lịch|huy lich|huỷ lịch|hủy lịch|xoa su kien|xóa sự kiện|huy su kien|hủy sự kiện|delete event|cancel event)\\s*/i, '')\n  .replace(/\\b(hom nay|ngay mai|mai|ngay kia|tuan sau|tuan nay|cuoi tuan nay|cuoi tuan sau|thu\\s*[2-7]|chu nhat)\\b/gi, '')\n  .replace(/\\s+/g, ' ')\n  .trim();",
        label="calendar_delete query",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, payload, message, rawText: raw, text, chatId, calendarId, query: hasDeleteQuery ? query : '__missing_delete_target__', hasDeleteQuery, after: iso(afterDate, afterDate.getHours(), afterDate.getMinutes(), 0), before: iso(beforeDate, beforeDate.getHours(), beforeDate.getMinutes(), 59), response: hasDeleteQuery ? '' : guidance } }];",
        "return [{ json: { ...source, payload, message, rawText: raw, text, chatId, calendarId, directEventId, query: hasDeleteQuery ? query : '__missing_delete_target__', hasDeleteQuery, after: iso(afterDate, afterDate.getHours(), afterDate.getMinutes(), 0), before: iso(beforeDate, beforeDate.getHours(), beforeDate.getMinutes(), 59), response: hasDeleteQuery || directEventId ? '' : guidance } }];",
        label="calendar_delete return",
    )
    return code


def patch_calendar_delete_pick(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Chuan Bi Xoa Lich').item.json;\nif (!source.hasDeleteQuery) {\n  return [{ json: { ...source, canDelete: false } }];\n}",
        "const source = $('Chuan Bi Xoa Lich').item.json;\nif (source.directEventId) {\n  return [{ json: { ...source, canDelete: true, eventId: source.directEventId, summary: source.query || 'Sự kiện đã chọn', start: '', end: '' } }];\n}\nif (!source.hasDeleteQuery) {\n  return [{ json: { ...source, canDelete: false } }];\n}",
        label="calendar_delete pick directEventId",
    )
    return code


def patch_calendar_check_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst raw = source.rawText;\nconst text = source.text;",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst raw = String(source.rawText || source.text || args.date || args.startAt || args.endAt || '').trim();\nconst text = String(source.text || source.rawText || args.date || '').trim();",
        label="calendar_check args",
    )
    code = replace_or_fail(
        code,
        "const date = parseTargetDate(text, now);",
        "const calendarId = String(source.calendarId || args.calendarId || source.payload?.calendarId || 'primary').trim();\nconst directStart = String(source.startAt || args.startAt || '').trim();\nconst directEnd = String(source.endAt || args.endAt || '').trim();\nconst explicitDate = String(source.date || args.date || '').trim();\nconst date = explicitDate ? startOfDay(new Date(explicitDate)) : parseTargetDate(text, now);",
        label="calendar_check direct fields",
    )
    code = replace_or_fail(
        code,
        "let start = '';\nlet end = '';",
        "let start = directStart;\nlet end = directEnd;",
        label="calendar_check start/end init",
    )
    code = replace_or_fail(
        code,
        "if (rangeMatch) {",
        "if (start && end) {\n  // structured args already provided\n} else if (rangeMatch) {",
        label="calendar_check bypass parse",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, start, end, isReady, response } }];",
        "return [{ json: { ...source, calendarId, start, end, isReady, response: isReady ? '' : response } }];",
        label="calendar_check return",
    )
    return code


def patch_gmail_read_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="gmail_read args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || source.query || args.query || message.text || payload.text || '').trim();",
        label="gmail_read raw",
    )
    code = replace_or_fail(
        code,
        "const query = raw\n  .replace(/^(doc mail|đọc mail|doc email|đọc email|noi dung mail|nội dung mail|noi dung email|nội dung email|read mail|read email|open mail|open email)\\s*/i, '')\n  .replace(/\\s+/g, ' ')\n  .trim();",
        "const explicitQuery = String(source.query || args.query || '').trim();\nconst query = (explicitQuery || raw)\n  .replace(/^(doc mail|đọc mail|doc email|đọc email|noi dung mail|nội dung mail|noi dung email|nội dung email|read mail|read email|open mail|open email)\\s*/i, '')\n  .replace(/\\s+/g, ' ')\n  .trim();\nconst messageId = String(source.messageId || args.messageId || '').trim();",
        label="gmail_read query/messageId",
    )
    code = replace_or_fail(
        code,
        "const hasQuery = Boolean(query);",
        "const hasQuery = Boolean(query || messageId);",
        label="gmail_read hasQuery",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, payload, message, chatId, query, hasQuery, response: hasQuery ? '' : guidance } }];",
        "return [{ json: { ...source, payload, message, chatId, query, messageId, hasQuery, response: hasQuery ? '' : guidance } }];",
        label="gmail_read return",
    )
    return code


def patch_gmail_draft_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="gmail_draft args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || payload.text || '').trim();",
        "const raw = String(source.rawText || source.text || payload.text || '').trim();",
        label="gmail_draft raw",
    )
    code = replace_or_fail(
        code,
        "let toEmail = '';\nlet subject = '';\nlet body = '';\nlet isReady = false;",
        "let toEmail = String(source.toEmail || source.to || args.toEmail || args.to || '').trim();\nlet subject = String(source.subject || args.subject || '').trim();\nlet body = String(source.body || args.body || '').trim();\nlet isReady = Boolean(toEmail && subject && body);",
        label="gmail_draft direct fields",
    )
    code = replace_or_fail(
        code,
        "if (emailMatch) {",
        "if (!isReady && emailMatch) {",
        label="gmail_draft parse fallback",
    )
    return code


def patch_gmail_reply_prepare(code: str) -> str:
    code = replace_or_fail(
        code,
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst payload = source.payload || {};",
        "const source = $('Execute Workflow Trigger').item.json || {};\nconst args = source.args || source.payload?.args || {};\nconst payload = source.payload || {};",
        label="gmail_reply args",
    )
    code = replace_or_fail(
        code,
        "const raw = String(source.rawText || message.text || '').trim();",
        "const raw = String(source.rawText || source.text || message.text || '').trim();",
        label="gmail_reply raw",
    )
    code = replace_or_fail(
        code,
        "let cleaned = raw.replace(/^(tra loi mail|trả lời mail|tra loi email|trả lời email|reply mail|reply email)\\s*/i, '').trim();",
        "let cleaned = raw.replace(/^(tra loi mail|trả lời mail|tra loi email|trả lời email|reply mail|reply email)\\s*/i, '').trim();\nconst explicitSearchQuery = String(source.searchQuery || args.searchQuery || '').trim();\nconst directMessageId = String(source.messageId || args.messageId || '').trim();\nconst directReplyBody = String(source.body || args.body || '').trim();",
        label="gmail_reply direct values",
    )
    code = replace_or_fail(
        code,
        "let searchQuery = '';\nlet replyBody = '';\nlet isReady = false;",
        "let searchQuery = explicitSearchQuery;\nlet replyBody = directReplyBody;\nlet isReady = Boolean(searchQuery && replyBody);",
        label="gmail_reply init",
    )
    code = replace_or_fail(
        code,
        "if (parts.length >= 2) {",
        "if (!isReady && parts.length >= 2) {",
        label="gmail_reply parts fallback",
    )
    code = replace_or_fail(
        code,
        "return [{ json: { ...source, chatId, searchQuery, replyBody, isReady, response: isReady ? '' : guidance } }];",
        "return [{ json: { ...source, chatId, messageId: directMessageId, searchQuery, replyBody, isReady, response: isReady ? '' : guidance } }];",
        label="gmail_reply return",
    )
    return code


def main() -> None:
    gateway = ROOT / "workflows/core/workflow_mia_tool_gateway.json"
    patch_node(gateway, "Prepare Tool Request", patch_gateway_prepare)

    patch_node(
        ROOT / "google/calendar/workflow_sub_google_calendar_delete_event.json",
        "Chuan Bi Xoa Lich",
        patch_calendar_delete_prepare,
    )
    patch_node(
        ROOT / "google/calendar/workflow_sub_google_calendar_delete_event.json",
        "Chon Lich Can Xoa",
        patch_calendar_delete_pick,
    )
    patch_node(
        ROOT / "google/calendar/workflow_sub_google_calendar_check_availability.json",
        "Chuan Bi Kiem Tra Ranh",
        patch_calendar_check_prepare,
    )
    patch_node(
        ROOT / "google/gmail/workflow_sub_google_gmail_read_email.json",
        "Chuan Bi Doc Email",
        patch_gmail_read_prepare,
    )
    patch_node(
        ROOT / "google/gmail/workflow_sub_google_gmail_draft_email.json",
        "Parse Draft Email",
        patch_gmail_draft_prepare,
    )
    patch_node(
        ROOT / "google/gmail/workflow_sub_google_gmail_reply_email.json",
        "Parse Tra Loi Email",
        patch_gmail_reply_prepare,
    )


if __name__ == "__main__":
    main()
