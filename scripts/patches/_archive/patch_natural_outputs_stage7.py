#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def save(rel: str, data: dict) -> None:
    (ROOT / rel).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def set_code(data: dict, node_name: str, code: str) -> None:
    for node in data.get("nodes", []):
        if node.get("name") == node_name:
            node.setdefault("parameters", {})["jsCode"] = code.strip() + "\n"
            return
    raise ValueError(f"Node not found: {node_name}")


GMAIL_SEARCH_FORMAT = r"""
const source = $('Chuan Bi Tim Email').item.json || {};

const pickFirst = (...values) => {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
};

const formatDate = (value) => {
  if (value === undefined || value === null || value === '') return '';
  const normalized = /^\d+$/.test(String(value)) ? Number(value) : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
};

const cleanText = (value = '') => String(value)
  .replace(/[\u034f\u061c\u115f\u1160\u17b4\u17b5\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/g, '')
  .replace(/\s+/g, ' ')
  .trim();

const buildMailLink = (email) => {
  const threadId = pickFirst(email.threadId);
  const messageId = pickFirst(email.id);
  if (threadId) return `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
  if (messageId) return `https://mail.google.com/mail/u/0/#inbox/${messageId}`;
  return '';
};

const rows = $input.all()
  .map((item) => item.json || {})
  .filter((email) => email.id || email.subject || email.Subject || email.from || email.From || email.snippet)
  .slice(0, 3);

const query = pickFirst(source.query, source.sender, source.subject);
const links = [];
let text = '';

if (!rows.length) {
  text = query
    ? `Mia chưa tìm thấy email nào khớp với "${query}".`
    : 'Mia chưa tìm thấy email phù hợp.';
} else {
  text = query
    ? `Mia tìm thấy ${rows.length} email khá khớp với "${query}":`
    : `Mia tìm thấy ${rows.length} email phù hợp:`;

  rows.forEach((email, index) => {
    const subject = pickFirst(email.subject, email.Subject, email.payload?.headers?.find((h) => h.name === 'Subject')?.value) || 'Không có tiêu đề';
    const from = cleanText(pickFirst(email.from?.value?.[0]?.name, email.from?.value?.[0]?.address, email.From, email.from, email.payload?.headers?.find((h) => h.name === 'From')?.value)) || 'Không rõ người gửi';
    const date = formatDate(pickFirst(email.date, email.Date, email.internalDate));
    const snippet = cleanText(pickFirst(email.snippet));
    const link = buildMailLink(email);

    text += `\n${index + 1}. ${subject} — từ ${from}`;
    if (date) text += `, lúc ${date}`;
    if (snippet) text += `\n   ${snippet.slice(0, 180)}`;
    if (link && !links.includes(link)) links.push(link);
  });

  if (links.length) {
    text += '\n\nMở nhanh email:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\n${index + 1}. ${link}`;
    });
  }
}

return [{
  json: {
    ok: true,
    tool: 'gmail.search_email',
    chatId: source.chatId || '',
    text: text.trim(),
    links: links.slice(0, 3),
    result: { emails: rows },
    meta: { query, count: rows.length }
  }
}];
"""


GMAIL_READ_FORMAT = r"""
const source = $('Chuan Bi Doc Email').item.json || {};

const pickFirst = (...values) => {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
};

const formatDate = (value) => {
  if (value === undefined || value === null || value === '') return '';
  const normalized = /^\d+$/.test(String(value)) ? Number(value) : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
};

const cleanText = (value = '') => String(value)
  .replace(/[\u034f\u061c\u115f\u1160\u17b4\u17b5\u180e\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]/g, '')
  .replace(/\s+/g, ' ')
  .trim();

const buildMailLink = (email) => {
  const threadId = pickFirst(email.threadId);
  const messageId = pickFirst(email.id);
  if (threadId) return `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
  if (messageId) return `https://mail.google.com/mail/u/0/#inbox/${messageId}`;
  return '';
};

const rows = $input.all()
  .map((item) => item.json || {})
  .filter((email) => email && Object.keys(email).length > 0 && (email.id || email.subject || email.Subject || email.from || email.From || email.snippet));

if (!rows.length) {
  const query = pickFirst(source.query, source.messageId);
  return [{
    json: {
      ok: false,
      tool: 'gmail.read_email',
      chatId: source.chatId || '',
      text: query ? `Mia chưa tìm thấy email phù hợp với "${query}".` : 'Mia chưa tìm thấy email phù hợp.',
      links: [],
      result: {},
      meta: { query }
    }
  }];
}

const email = rows[0];
const from = cleanText(pickFirst(email.from?.value?.[0]?.name, email.from?.value?.[0]?.address, email.From, email.from, email.payload?.headers?.find((h) => h.name === 'From')?.value)) || 'Không rõ người gửi';
const to = cleanText(pickFirst(email.to?.value?.[0]?.address, email.To, email.to, email.payload?.headers?.find((h) => h.name === 'To')?.value));
const subject = cleanText(pickFirst(email.subject, email.Subject, email.payload?.headers?.find((h) => h.name === 'Subject')?.value)) || 'Không có tiêu đề';
const date = formatDate(pickFirst(email.date, email.Date, email.internalDate));
const link = buildMailLink(email);

let body = cleanText(pickFirst(email.textPlain, email.text, email.snippet)) || '(Email này không có nội dung văn bản để hiển thị.)';
let truncated = false;
if (body.length > 1400) {
  body = body.slice(0, 1400).trimEnd();
  truncated = true;
}

let text = `Mia đọc được email "${subject}"`;
text += `\nTừ: ${from}`;
if (to) text += `\nĐến: ${to}`;
if (date) text += `\nThời gian: ${date}`;
if (link) text += `\nLink: ${link}`;
text += `\n\nNội dung:\n${body}`;
if (truncated) text += '\n\nMia đã rút gọn phần cuối để Telegram dễ đọc hơn.';

return [{
  json: {
    ok: true,
    tool: 'gmail.read_email',
    chatId: source.chatId || '',
    text: text.trim(),
    links: link ? [link] : [],
    result: { email },
    meta: { subject, from, date }
  }
}];
"""


CALENDAR_FIND_FORMAT = r"""
function toDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(date) {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(date);
}

function formatTime(date) {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date);
}

function formatRange(startValue, endValue) {
  const startDate = toDate(startValue);
  const endDate = toDate(endValue);
  if (!startDate) return startValue || '';
  if (!endDate) return `${formatTime(startDate)}, ${formatDate(startDate)}`;
  const sameDay = startDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }) === endDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
  if (sameDay) return `${formatTime(startDate)} - ${formatTime(endDate)}, ${formatDate(startDate)}`;
  return `${formatTime(startDate)}, ${formatDate(startDate)} đến ${formatTime(endDate)}, ${formatDate(endDate)}`;
}

const source = $('Chuan Bi Tim Lich').item.json || {};
const rows = $input.all()
  .map((item) => item.json || {})
  .filter((event) => event && Object.keys(event).length > 0 && (event.id || event.summary || event.start || event.end))
  .slice(0, 3);
const query = source.query || source.rawText || '';
const links = [];

let text = '';
if (!rows.length) {
  text = query
    ? `Mia chưa tìm thấy lịch nào khớp với "${query}".`
    : 'Mia chưa tìm thấy lịch phù hợp.';
} else {
  text = query
    ? `Mia tìm thấy ${rows.length} lịch khá khớp với "${query}":`
    : `Mia tìm thấy ${rows.length} lịch phù hợp:`;
  rows.forEach((event, index) => {
    const title = event.summary || 'Không có tiêu đề';
    const start = event.start?.dateTime || event.start?.date || '';
    const end = event.end?.dateTime || event.end?.date || '';
    text += `\n${index + 1}. ${title} — ${formatRange(start, end)}`;
    if (event.htmlLink && !links.includes(event.htmlLink)) links.push(event.htmlLink);
  });
  if (links.length) {
    text += '\n\nMở nhanh lịch:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\n${index + 1}. ${link}`;
    });
  }
}

return [{
  json: {
    ok: true,
    tool: 'calendar.find_event',
    chatId: source.chatId || '',
    text: text.trim(),
    links: links.slice(0, 3),
    result: { events: rows },
    meta: { query, count: rows.length }
  }
}];
"""


CALENDAR_AVAILABILITY_FORMAT = r"""
function toDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(date) {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  }).format(date);
}

function formatTime(date) {
  return new Intl.DateTimeFormat('vi-VN', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false
  }).format(date);
}

function formatRange(startValue, endValue) {
  const startDate = toDate(startValue);
  const endDate = toDate(endValue);
  if (!startDate) return startValue || '';
  if (!endDate) return `${formatTime(startDate)}, ${formatDate(startDate)}`;
  const sameDay = startDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }) === endDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
  if (sameDay) return `${formatTime(startDate)} - ${formatTime(endDate)}, ${formatDate(startDate)}`;
  return `${formatTime(startDate)}, ${formatDate(startDate)} đến ${formatTime(endDate)}, ${formatDate(endDate)}`;
}

const source = $('Chuan Bi Kiem Tra Ranh').item.json || {};
const conflicts = $input.all().map((item) => item.json || {}).filter((event) => event.id || event.summary);
const available = conflicts.length === 0;

let text = `Mia kiểm tra khung ${formatRange(source.start, source.end)} rồi. `;
if (available) {
  text += 'Khung này đang rảnh.';
} else {
  text += `Khung này đang vướng ${conflicts.length} lịch:`;
  conflicts.slice(0, 3).forEach((event, index) => {
    const title = event.summary || 'Không có tiêu đề';
    const start = event.start?.dateTime || event.start?.date || '';
    const end = event.end?.dateTime || event.end?.date || '';
    text += `\n${index + 1}. ${title} — ${formatRange(start, end)}`;
  });
}

return [{
  json: {
    ok: true,
    tool: 'calendar.check_availability',
    chatId: source.chatId || '',
    text: text.trim(),
    links: [],
    result: { available, conflicts: conflicts.slice(0, 3) },
    meta: { start: source.start || '', end: source.end || '' }
  }
}];
"""


DOCS_READ_FORMAT = r"""
function collectText(node, out = []) {
  if (Array.isArray(node)) {
    node.forEach((item) => collectText(item, out));
    return out;
  }
  if (!node || typeof node !== 'object') return out;
  if (node.textRun && typeof node.textRun.content === 'string') out.push(node.textRun.content);
  Object.values(node).forEach((value) => collectText(value, out));
  return out;
}

const source = $('Prepare Action').item.json || {};
const doc = $input.item.json || {};
const docId = doc.documentId || source.docId || '';
const title = doc.title || source.docName || 'Không rõ tên';
const link = source.webViewLink || (docId ? `https://docs.google.com/document/d/${docId}/edit` : '');
const content = collectText(doc.body?.content || []).join('').replace(/\n{3,}/g, '\n\n').trim();
let preview = content.slice(0, 1000) || '(Tài liệu này đang trống.)';
const truncated = content.length > 1000;

let text = `Mia đọc được Google Doc "${title}".`;
if (link) text += `\nLink: ${link}`;
text += `\n\nXem trước:\n${preview}`;
if (truncated) text += '\n\nMia đã rút gọn nội dung để tiết kiệm ngữ cảnh.';

return [{
  json: {
    ok: true,
    tool: 'docs.read_doc',
    chatId: source.chatId || '',
    text: text.trim(),
    links: link ? [link] : [],
    result: { documentId: docId, title, preview },
    meta: { truncated, contentLength: content.length }
  }
}];
"""


SHEETS_READ_FORMAT = r"""
function getJson(nodeName) {
  try {
    return $(nodeName).item.json || {};
  } catch (e) {
    return {};
  }
}

const source = {
  ...getJson('Prepare Action'),
  ...getJson('Resolve Search Result')
};
const result = $input.item.json || {};
const rows = Array.isArray(result.values) ? result.values : [];
const limited = rows.slice(0, 10);
let preview = limited.map((row, index) => `${index + 1}. ${row.map((cell) => String(cell)).join(' | ')}`).join('\n');
let truncated = rows.length > 10;
if (preview.length > 1000) {
  preview = preview.slice(0, 1000).trimEnd();
  truncated = true;
}

const sheetId = source.spreadsheetId || source.sheetId || '';
const title = source.sheetName || source.name || 'Không rõ tên';
const link = source.webViewLink || (sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit` : '');
const shownRange = source.sheetTab ? `'${source.sheetTab}'!${source.range || 'A1:Z30'}` : (source.range || 'A1:Z30');

let text = `Mia đọc được Google Sheet "${title}" ở range ${shownRange}.`;
if (link) text += `\nLink: ${link}`;
text += `\n\nDữ liệu xem trước:\n${preview || '(Range này chưa có dữ liệu.)'}`;
if (truncated) text += '\n\nMia đã rút gọn bảng để Telegram dễ đọc hơn.';

return [{
  json: {
    ok: true,
    tool: 'sheets.read_sheet',
    chatId: source.chatId || result.chatId || '',
    text: text.trim(),
    links: link ? [link] : [],
    result: { spreadsheetId: sheetId, title, range: shownRange, rows: limited },
    meta: { truncated, rowCount: rows.length }
  }
}];
"""


GATEWAY_NORMALIZE = r"""
const source = $('Prepare Tool Request').item.json || {};
const output = $json || {};

function decodeEntities(value = '') {
  return String(value)
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'");
}

function htmlToPlainText(value = '') {
  return decodeEntities(String(value || ''))
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n\n')
    .replace(/<\/div>/gi, '\n')
    .replace(/<\/li>/gi, '\n')
    .replace(/<li>/gi, '- ')
    .replace(/<\/h\d>/gi, '\n')
    .replace(/<a[^>]*href="([^"]+)"[^>]*>(.*?)<\/a>/gi, '$2: $1')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\s+([,.;:!?])/g, '$1')
    .replace(/\n\s+/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function extractUrls(value = '') {
  const seen = [];
  const matches = String(value || '').match(/https?:\/\/[^\s)>\]]+/g) || [];
  for (const match of matches) {
    const cleaned = match.replace(/[.,;]+$/, '');
    if (cleaned && !seen.includes(cleaned)) seen.push(cleaned);
  }
  return seen;
}

function capVisibleLinks(text, limit = 3) {
  const urls = extractUrls(text);
  if (urls.length <= limit) return text;
  const extra = new Set(urls.slice(limit));
  const lines = [];
  for (let line of String(text || '').split('\n')) {
    const lineUrls = extractUrls(line);
    if (lineUrls.length && lineUrls.every((url) => extra.has(url))) continue;
    for (const url of lineUrls) {
      if (extra.has(url)) line = line.replace(url, '').replace(/[ .:-]+$/, '');
    }
    lines.push(line.trimEnd());
  }
  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
}

const raw = String(
  output.response ||
  output.text ||
  output.output ||
  output.responseText ||
  ''
).replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

const text = capVisibleLinks(htmlToPlainText(raw) || raw || JSON.stringify(output), 3);
const outputLinks = Array.isArray(output.links) ? output.links.filter(Boolean) : [];
const links = [...outputLinks, ...extractUrls(text)].filter((url, index, arr) => arr.indexOf(url) === index).slice(0, 3);

return [{
  json: {
    ok: output.ok !== false,
    tool: output.tool || source.tool || '',
    workflowKey: source.workflowKey || '',
    requestId: source.requestId || '',
    text,
    result: output.result || output.data || output.payload || {},
    links,
    meta: {
      ...(output.meta || {}),
      deliveryMode: source.deliveryMode || 'return',
      originChatId: source.originChatId || '',
    },
    data: output,
  }
}];
"""


PATCHES = [
    ("google/gmail/workflow_sub_google_gmail_search_email.json", "Format Tim Email", GMAIL_SEARCH_FORMAT),
    ("google/gmail/workflow_sub_google_gmail_read_email.json", "Format Noi Dung Email", GMAIL_READ_FORMAT),
    ("google/calendar/workflow_sub_google_calendar_find_event.json", "Format Tim Lich", CALENDAR_FIND_FORMAT),
    ("google/calendar/workflow_sub_google_calendar_check_availability.json", "Format Kiem Tra Ranh", CALENDAR_AVAILABILITY_FORMAT),
    ("google/docs/workflow_sub_google_docs_read_doc.json", "Format Action", DOCS_READ_FORMAT),
    ("google/sheets/workflow_sub_google_sheets_read_sheet.json", "Format Action", SHEETS_READ_FORMAT),
    ("workflows/core/workflow_mia_tool_gateway.json", "Normalize Tool Result", GATEWAY_NORMALIZE),
]


def main() -> None:
    touched: set[str] = set()
    for rel, node, code in PATCHES:
        data = load(rel)
        set_code(data, node, code)
        save(rel, data)
        touched.add(rel)

    for rel in sorted(touched):
        print(rel)


if __name__ == "__main__":
    main()
