#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

WORKFLOW_UPDATES: dict[Path, dict[str, object]] = {
    ROOT / "workflows/core/workflow_mia_tool_gateway.json": {
        "Prepare Tool Request": r"""
const source = $('Webhook Tool Request').item.json || {};
const body = source.body || source;
const headers = source.headers || {};
const expectedToken = String($env.MIA_TOOL_GATEWAY_TOKEN || '').trim();
const providedToken = String(headers['x-mia-tool-token'] || headers['X-Mia-Tool-Token'] || '').trim();

if (expectedToken && providedToken !== expectedToken) {
  return [{ json: { ok: false, error: 'Unauthorized tool gateway token.' } }];
}

const tool = String(body.tool || '').trim();
const args = body.args && typeof body.args === 'object' ? body.args : {};
const requestId = String(body.requestId || '').trim();
const originChatId = String(body.chatId || '').trim();
const deliveryMode = String(body.deliveryMode || 'return').trim() || 'return';
const backendChatId = deliveryMode === 'telegram' ? originChatId : '';

function clean(value) {
  return String(value || '').trim();
}

const toolConfig = {
  'weather.get': {
    workflowKey: 'weather',
    build: (a) => ({
      text: `thời tiết ${clean(a.location)}`.trim(),
      location: clean(a.location),
    }),
  },
  'gold.get_price': {
    workflowKey: 'gold',
    build: () => ({ text: 'giá vàng hôm nay' }),
  },
  'news.get': {
    workflowKey: 'news',
    build: (a) => ({
      text: clean(a.topic) ? `tin tức ${clean(a.topic)}` : 'tin tức hôm nay',
      topic: clean(a.topic),
    }),
  },
  'search.web': {
    workflowKey: 'search',
    build: (a) => ({
      text: `tìm kiếm ${clean(a.query)}`.trim(),
      query: clean(a.query),
    }),
  },

  'calendar.help': {
    workflowKey: 'calendar.help',
    build: () => ({ text: 'calendar help' }),
  },
  'calendar.list_today': {
    workflowKey: 'calendar.list_today',
    build: () => ({ text: 'lịch hôm nay' }),
  },
  'calendar.list_tomorrow': {
    workflowKey: 'calendar.list_tomorrow',
    build: () => ({ text: 'lịch ngày mai' }),
  },
  'calendar.find_event': {
    workflowKey: 'calendar.find_event',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm sự kiện ${clean(a.query)}` : 'tìm sự kiện lịch'),
      query: clean(a.query),
      dateFrom: clean(a.dateFrom),
      dateTo: clean(a.dateTo),
      limit: Number(a.limit || 5) || 5,
    }),
  },
  'calendar.create_event': {
    workflowKey: 'calendar.create_event',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.title || a.summary) ? `tạo lịch ${clean(a.title || a.summary)}` : 'tạo lịch'),
      title: clean(a.title || a.summary),
      summary: clean(a.summary || a.title),
      startAt: clean(a.startAt),
      endAt: clean(a.endAt),
      timezone: clean(a.timezone),
      description: clean(a.description),
      location: clean(a.location),
      calendarId: clean(a.calendarId),
    }),
  },
  'calendar.delete_event': {
    workflowKey: 'calendar.delete_event',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.eventId) ? `xóa lịch ${clean(a.eventId)}` : 'xóa lịch'),
      eventId: clean(a.eventId),
      query: clean(a.query),
    }),
  },
  'calendar.check_availability': {
    workflowKey: 'calendar.check_availability',
    build: (a) => ({
      text: clean(a.instruction) || 'kiểm tra lịch rảnh',
      date: clean(a.date),
      dateFrom: clean(a.dateFrom),
      dateTo: clean(a.dateTo),
      timezone: clean(a.timezone),
    }),
  },

  'gmail.help': {
    workflowKey: 'gmail.help',
    build: () => ({ text: 'gmail help' }),
  },
  'gmail.list_inbox': {
    workflowKey: 'gmail.list_inbox',
    build: () => ({ text: 'xem mail' }),
  },
  'gmail.read_email': {
    workflowKey: 'gmail.read_email',
    build: (a) => ({ text: clean(a.instruction) || 'đọc email', messageId: clean(a.messageId) }),
  },
  'gmail.search_email': {
    workflowKey: 'gmail.search_email',
    build: (a) => ({
      text:
        clean(a.instruction) ||
        (clean(a.query) ? `tìm email ${clean(a.query)}` : 'tìm email'),
      query: clean(a.query),
      sender: clean(a.sender),
      subject: clean(a.subject),
      limit: Number(a.limit || 3) || 3,
    }),
  },
  'gmail.send_email': {
    workflowKey: 'gmail.send_email',
    build: (a) => ({
      text:
        clean(a.instruction) ||
        [clean(a.to || a.toEmail), clean(a.subject)].filter(Boolean).join(' ') ||
        'gửi email',
      to: clean(a.to || a.toEmail),
      toEmail: clean(a.toEmail || a.to),
      subject: clean(a.subject),
      body: clean(a.body),
    }),
  },
  'gmail.draft_email': {
    workflowKey: 'gmail.draft_email',
    build: (a) => ({
      text: clean(a.instruction) || 'soạn email',
      to: clean(a.to || a.toEmail),
      toEmail: clean(a.toEmail || a.to),
      subject: clean(a.subject),
      body: clean(a.body),
    }),
  },
  'gmail.reply_email': {
    workflowKey: 'gmail.reply_email',
    build: (a) => ({
      text: clean(a.instruction) || 'trả lời email',
      messageId: clean(a.messageId),
      body: clean(a.body),
    }),
  },

  'drive.help': {
    workflowKey: 'drive.help',
    build: () => ({ text: 'drive help' }),
  },
  'drive.list_files': {
    workflowKey: 'drive.list_files',
    build: (a) => ({
      text: 'xem file drive',
      limit: Number(a.limit || 3) || 3,
      folderId: clean(a.folderId),
      mimeType: clean(a.mimeType),
    }),
  },
  'drive.search_file': {
    workflowKey: 'drive.search_file',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm file ${clean(a.query)}` : 'tìm file'),
      query: clean(a.query),
      fileName: clean(a.fileName || a.query),
      mimeType: clean(a.mimeType),
      folderId: clean(a.folderId),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'drive.get_file_info': {
    workflowKey: 'drive.get_file_info',
    build: (a) => ({ text: clean(a.instruction) || 'xem chi tiết file', fileId: clean(a.fileId) }),
  },
  'drive.create_folder': {
    workflowKey: 'drive.create_folder',
    build: (a) => ({ text: clean(a.instruction) || 'tạo folder', name: clean(a.name), parentId: clean(a.parentId) }),
  },
  'drive.create_file': {
    workflowKey: 'drive.create_file',
    build: (a) => ({ text: clean(a.instruction) || 'tạo file', name: clean(a.name), content: clean(a.content), mimeType: clean(a.mimeType), parentId: clean(a.parentId) }),
  },
  'drive.upload_file': {
    workflowKey: 'drive.upload_file',
    build: (a) => ({ text: clean(a.instruction) || 'upload file' }),
  },
  'drive.download_file': {
    workflowKey: 'drive.download_file',
    build: (a) => ({ text: clean(a.instruction) || 'tải file', fileId: clean(a.fileId) }),
  },
  'drive.share_file': {
    workflowKey: 'drive.share_file',
    build: (a) => ({ text: clean(a.instruction) || 'share file', fileId: clean(a.fileId), email: clean(a.email), role: clean(a.role) }),
  },
  'drive.move_file': {
    workflowKey: 'drive.move_file',
    build: (a) => ({ text: clean(a.instruction) || 'di chuyển file', fileId: clean(a.fileId), targetFolderId: clean(a.targetFolderId) }),
  },
  'drive.rename_file': {
    workflowKey: 'drive.rename_file',
    build: (a) => ({ text: clean(a.instruction) || 'đổi tên file', fileId: clean(a.fileId), newName: clean(a.newName) }),
  },
  'drive.copy_file': {
    workflowKey: 'drive.copy_file',
    build: (a) => ({ text: clean(a.instruction) || 'copy file', fileId: clean(a.fileId), newName: clean(a.newName), parentId: clean(a.parentId) }),
  },
  'drive.delete_file': {
    workflowKey: 'drive.delete_file',
    build: (a) => ({ text: clean(a.instruction) || 'xóa file', fileId: clean(a.fileId) }),
  },
  'drive.delete_folder': {
    workflowKey: 'drive.delete_folder',
    build: (a) => ({ text: clean(a.instruction) || 'xóa folder', folderId: clean(a.folderId) }),
  },
  'drive.export_file': {
    workflowKey: 'drive.export_file',
    build: (a) => ({ text: clean(a.instruction) || 'export file', fileId: clean(a.fileId), mimeType: clean(a.mimeType) }),
  },

  'docs.help': {
    workflowKey: 'docs.help',
    build: () => ({ text: 'docs help' }),
  },
  'docs.search_doc': {
    workflowKey: 'docs.search_doc',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm doc ${clean(a.query)}` : 'tìm doc'),
      query: clean(a.query),
      docName: clean(a.docName || a.query),
      folderId: clean(a.folderId),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'docs.read_doc': {
    workflowKey: 'docs.read_doc',
    build: (a) => ({ text: clean(a.instruction) || 'xem doc', documentId: clean(a.documentId), maxChars: Number(a.maxChars || 0) || 0 }),
  },
  'docs.create_doc': {
    workflowKey: 'docs.create_doc',
    build: (a) => ({ text: clean(a.instruction) || 'tạo doc', title: clean(a.title), content: clean(a.content), folderId: clean(a.folderId) }),
  },
  'docs.append_doc': {
    workflowKey: 'docs.append_doc',
    build: (a) => ({ text: clean(a.instruction) || 'thêm vào doc', documentId: clean(a.documentId), content: clean(a.content) }),
  },
  'docs.delete_doc': {
    workflowKey: 'docs.delete_doc',
    build: (a) => ({ text: clean(a.instruction) || 'xóa doc', documentId: clean(a.documentId) }),
  },

  'sheets.help': {
    workflowKey: 'sheets.help',
    build: () => ({ text: 'sheets help' }),
  },
  'sheets.search_sheet': {
    workflowKey: 'sheets.search_sheet',
    build: (a) => ({
      text: clean(a.instruction) || (clean(a.query) ? `tìm sheet ${clean(a.query)}` : 'tìm sheet'),
      query: clean(a.query),
      sheetName: clean(a.sheetName || a.query),
      folderId: clean(a.folderId),
      limit: Number(a.limit || 10) || 10,
    }),
  },
  'sheets.read_sheet': {
    workflowKey: 'sheets.read_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'xem sheet', spreadsheetId: clean(a.spreadsheetId), sheetName: clean(a.sheetName), range: clean(a.range), maxRows: Number(a.maxRows || 0) || 0 }),
  },
  'sheets.create_sheet': {
    workflowKey: 'sheets.create_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'tạo sheet', title: clean(a.title), sheetName: clean(a.sheetName) }),
  },
  'sheets.append_row': {
    workflowKey: 'sheets.append_row',
    build: (a) => ({ text: clean(a.instruction) || 'thêm dòng vào sheet', spreadsheetId: clean(a.spreadsheetId), sheetName: clean(a.sheetName), values: a.values || [] }),
  },
  'sheets.update_cell': {
    workflowKey: 'sheets.update_cell',
    build: (a) => ({ text: clean(a.instruction) || 'cập nhật sheet', spreadsheetId: clean(a.spreadsheetId), sheetName: clean(a.sheetName), cell: clean(a.cell), value: clean(a.value) }),
  },
  'sheets.delete_sheet': {
    workflowKey: 'sheets.delete_sheet',
    build: (a) => ({ text: clean(a.instruction) || 'xóa sheet', spreadsheetId: clean(a.spreadsheetId) }),
  },

  'shortlink.create': {
    workflowKey: 'shortlink.create',
    build: (a) => {
      const url = clean(a.url);
      const ttl = clean(a.ttl);
      return {
        text: ttl ? `rút gọn link ${url} ${ttl}` : `rút gọn link ${url}`,
        url,
        ttl,
      };
    },
  },
};

if (!tool) {
  return [{ json: { ok: false, error: 'Missing tool name.' } }];
}

const config = toolConfig[tool];
if (!config) {
  return [{ json: { ok: false, error: `Unsupported or invalid tool request: ${tool}` } }];
}

const built = config.build(args || {});
const text = clean(built.text);
if (!text) {
  return [{ json: { ok: false, error: `Unsupported or invalid tool request: ${tool}` } }];
}

return [{
  json: {
    ok: true,
    tool,
    workflowKey: config.workflowKey,
    text,
    rawText: text,
    chatId: backendChatId,
    originChatId,
    requestId,
    deliveryMode,
    args,
    payload: { tool, args, requestId, originChatId, deliveryMode },
    message: { text, caption: text },
    ...built,
  }
}];
""",
        "Normalize Tool Result": r"""
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

const raw = String(
  output.text ||
  output.output ||
  output.response ||
  output.responseText ||
  ''
).replace(/<think>[\s\S]*?<\/think>/gi, '').trim();

const text = htmlToPlainText(raw) || raw || JSON.stringify(output);
const links = extractUrls(text);

return [{
  json: {
    ok: true,
    tool: source.tool || '',
    workflowKey: source.workflowKey || '',
    requestId: source.requestId || '',
    text,
    result: output.result || output.data || output.payload || {},
    links,
    meta: {
      deliveryMode: source.deliveryMode || 'return',
      originChatId: source.originChatId || '',
    },
    data: output,
  }
}];
""",
    },
    ROOT / "google/gmail/workflow_sub_google_gmail_search_email.json": {
        "Chuan Bi Tim Email": r"""
const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';
const raw = String(source.rawText || source.text || message.text || payload.text || '').trim();

function clean(value) {
  return String(value || '').trim();
}

const query = clean(
  source.query ||
  payload.query ||
  raw.replace(/^(tim mail|tìm mail|tim email|tìm email|search mail|search email|tim kiem mail|tìm kiếm mail|tim kiem email|tìm kiếm email)\s*/i, '')
);
const sender = clean(source.sender || payload.sender);
const subject = clean(source.subject || payload.subject);
const limit = Number(source.limit || payload.limit || 3) || 3;
const hasQuery = Boolean(query || sender || subject);
const guidance = '🔎 <b>Tìm kiếm email</b>\n\nVí dụ: tìm mail từ Google';

return [{
  json: {
    ...source,
    payload,
    message,
    chatId,
    query,
    sender,
    subject,
    limit,
    hasQuery,
    response: hasQuery ? '' : guidance
  }
}];
""",
        "Gmail Search": {
            "operation": "getAll",
            "limit": "={{ $json.limit }}",
            "filters": {
                "search": "={{ [$json.query, $json.sender ? ('from:' + $json.sender) : '', $json.subject ? ('subject:' + $json.subject) : ''].filter(Boolean).join(' ') }}"
            }
        },
    },
    ROOT / "google/gmail/workflow_sub_google_gmail_send_email.json": {
        "Parse Gui Email": r"""
const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';
const raw = String(source.rawText || source.text || message.text || payload.text || '').trim();

const structuredTo = String(source.toEmail || source.to || payload.toEmail || payload.to || '').trim();
const structuredSubject = String(source.subject || payload.subject || '').trim();
const structuredBody = String(source.body || payload.body || '').trim();

const isDraftSend = /^(gui nhap|gửi nháp|gui email nhap|gửi email nháp|gui mail nhap|gửi mail nháp|send draft)\s*/i.test(raw);

let cleaned = raw
  .replace(/^(gui nhap|gửi nháp|gui email nhap|gửi email nháp|gui mail nhap|gửi mail nháp|send draft|gui mail|gửi mail|gui email|gửi email|send mail|send email)\s*/i, '')
  .trim();

let toEmail = structuredTo;
let subject = structuredSubject;
let body = structuredBody;
let isReady = Boolean(toEmail && subject && body);

if (!isReady) {
  const emailMatch = cleaned.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/);
  if (emailMatch) {
    toEmail = emailMatch[1];
    const remaining = cleaned.replace(toEmail, '').trim();
    const lines = remaining.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.length >= 2) {
      subject = lines[0];
      body = lines.slice(1).join('\n');
      isReady = true;
    } else if (lines.length === 1) {
      const parts = lines[0].split(/\s{2,}|\t/);
      if (parts.length >= 2) {
        subject = parts[0];
        body = parts.slice(1).join(' ');
        isReady = true;
      } else {
        subject = lines[0];
        body = lines[0];
        isReady = true;
      }
    }
  }
}

let guidance;
if (isDraftSend) {
  guidance = '📤 <b>Gửi email nháp</b>\n\nBạn hãy nhập theo mẫu:\n<code>gửi nháp email@example.com Tiêu đề\nNội dung email</code>\n\nVí dụ:\n<code>gửi nháp test@gmail.com Chào bạn\nXin chào, đây là email test.</code>';
} else {
  guidance = '📧 <b>Gửi email</b>\n\nBạn hãy nhập theo mẫu:\n<code>gửi mail email@example.com Tiêu đề\nNội dung email</code>\n\nVí dụ:\n<code>gửi mail test@gmail.com Chào bạn\nXin chào, đây là email test.</code>\n\nNếu chỉ muốn lưu nháp, dùng:\n<code>soạn mail email@example.com Tiêu đề\nNội dung email</code>\n\nNếu muốn gửi email nháp đã soạn, dùng:\n<code>gửi nháp email@example.com Tiêu đề\nNội dung email</code>';
}
return [{ json: { ...source, payload, message, chatId, toEmail, subject, body, isReady, isDraftSend, response: isReady ? '' : guidance } }];
""",
    },
    ROOT / "google/calendar/workflow_sub_google_calendar_create_event.json": {
        "Parse Tao Lich": r"""
const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};

function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\u0111/g, 'd')
    .replace(/\u0110/g, 'D');
}

const raw = String(source.rawText || source.text || message.text || payload.text || '').trim();
const text = normalize(source.text || raw);
const rawNormalized = normalize(raw);
const chatId = source.chatId || message.chat?.id || payload.chatId || '';
const calendarId = source.calendarId || payload.calendarId || 'kuminhuynhdoan@gmail.com';
const structuredSummary = String(source.summary || source.title || payload.summary || payload.title || '').trim();
const structuredStart = String(source.startAt || source.start || payload.startAt || payload.start || '').trim();
const structuredEnd = String(source.endAt || source.end || payload.endAt || payload.end || '').trim();
const structuredTimezone = String(source.timezone || payload.timezone || '').trim();
const structuredDescription = String(source.description || payload.description || raw).trim();
const structuredLocation = String(source.location || payload.location || '').trim();

const tzOffset = '+07:00';
const now = new Date();
const timeToken = '(\\d{1,2})(?:(?::|g|h)(\\d{1,2}))?\\s*h?';

function pad(n) { return String(n).padStart(2, '0'); }
function buildIso(date, hour, minute) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(hour)}:${pad(minute)}:00${tzOffset}`;
}
function startOfDay(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}
function addDays(base, days) {
  const d = new Date(base);
  d.setDate(d.getDate() + days);
  return d;
}
function nextWeekday(base, targetDow, nextWeek = false) {
  const d = startOfDay(base);
  const currentDow = d.getDay();
  let diff = (targetDow - currentDow + 7) % 7;
  if (diff === 0) diff = 7;
  if (nextWeek) diff += 7;
  d.setDate(d.getDate() + diff);
  return d;
}
function parseTargetDate(text, base) {
  if (/cuoi tuan sau/.test(text)) return startOfDay(nextWeekday(base, 6, true));
  if (/cuoi tuan nay/.test(text)) return startOfDay(nextWeekday(base, 6, false));
  const weekdayMatch = text.match(/thu\s*(2|3|4|5|6|7)|chu nhat/);
  if (weekdayMatch) {
    let targetDow = 0;
    if (weekdayMatch[1]) targetDow = Number(weekdayMatch[1]) - 1;
    return startOfDay(nextWeekday(base, targetDow, /tuan sau/.test(text)));
  }
  if (/ngay kia|mot ngay nua/.test(text)) return startOfDay(addDays(base, 2));
  if (/ngay mai|mai/.test(text)) return startOfDay(addDays(base, 1));
  return startOfDay(base);
}
function to24Hour(hour, ampm, contextText) {
  let value = Number(hour);
  const marker = String(ampm || '').toLowerCase();
  if (marker === 'pm' && value < 12) value += 12;
  if (marker === 'am' && value === 12) value = 0;
  if (!marker && /\b(chieu|toi)\b/.test(contextText) && value < 12) value += 12;
  return value;
}
function parseTimeInfo(text) {
  let startHour = null;
  let startMinute = 0;
  let endHour = null;
  let endMinute = 0;
  const rangeRegex = new RegExp(`(?:tu\\s*)?${timeToken}\\s*(am|pm)?\\s*(?:-|den|toi)\\s*${timeToken}\\s*(am|pm)?`, 'i');
  const startRegex = new RegExp(`(?:bat dau luc|luc|vao|tu)\\s*${timeToken}\\s*(am|pm)?`, 'i');
  const fallbackStartRegex = new RegExp(`${timeToken}\\s*(am|pm)?`, 'i');
  const explicitEndRegex = new RegExp(`(?:ket thuc luc|ket thuc|den|toi)\\s*${timeToken}\\s*(am|pm)?`, 'i');
  const rangeMatch = text.match(rangeRegex);
  const startMatch = text.match(startRegex) || text.match(fallbackStartRegex);
  const explicitEndMatch = text.match(explicitEndRegex);
  if (rangeMatch) {
    startHour = to24Hour(rangeMatch[1], rangeMatch[3], text);
    startMinute = Number(rangeMatch[2] || 0);
    endHour = to24Hour(rangeMatch[4], rangeMatch[6], text);
    endMinute = Number(rangeMatch[5] || 0);
  } else if (startMatch) {
    startHour = to24Hour(startMatch[1], startMatch[3], text);
    startMinute = Number(startMatch[2] || 0);
    if (explicitEndMatch) {
      endHour = to24Hour(explicitEndMatch[1], explicitEndMatch[3], text);
      endMinute = Number(explicitEndMatch[2] || 0);
    }
  } else if (/buoi sang|sang/.test(text)) {
    startHour = 9;
  } else if (/buoi chieu|chieu/.test(text)) {
    startHour = 14;
  } else if (/buoi toi|toi/.test(text)) {
    startHour = 19;
  } else if (/trua/.test(text)) {
    startHour = 12;
  }
  let durationMinutes = 60;
  const verboseDurationMatch = text.match(/(?:trong|khoang|keo dai)\s*(\d+)\s*(tieng|gio|h|phut)/i);
  const compactDurationMatch = text.match(/\b(\d+)\s*(tieng|gio|phut)\b/i);
  if (verboseDurationMatch) {
    durationMinutes = Number(verboseDurationMatch[1]) * (/phut/.test(verboseDurationMatch[2]) ? 1 : 60);
  } else if (compactDurationMatch) {
    durationMinutes = Number(compactDurationMatch[1]) * (/phut/.test(compactDurationMatch[2]) ? 1 : 60);
  } else if (/nua tieng|30 phut/.test(text)) {
    durationMinutes = 30;
  } else if (/2 tieng/.test(text)) {
    durationMinutes = 120;
  }
  return { startHour, startMinute, endHour, endMinute, durationMinutes };
}
function cleanupSummary(input) {
  return String(input || '')
    .replace(/^(tạo lịch|đặt lịch|thêm lịch|tạo sự kiện|đặt sự kiện|book lịch|create event|tao lich|dat lich|them lich|tao su kien)\s*/i, '')
    .replace(/\b(hôm nay|ngày mai|mai|ngày kia|tuần sau|tuần này|cuối tuần này|cuối tuần sau|thứ\s*[2-7]|chủ nhật|hom nay|ngay mai|ngay kia|tuan sau|tuan nay|cuoi tuan nay|cuoi tuan sau|thu\s*[2-7]|chu nhat)\b/gi, ' ')
    .replace(/(?:từ\s*)?\d{1,2}(?:(?::|g|h)\d{1,2})?\s*h?\s*(?:am|pm)?\s*(?:-|đến|toi|den)\s*\d{1,2}(?:(?::|g|h)\d{1,2})?\s*h?\s*(?:am|pm)?/gi, ' ')
    .replace(/(?:bắt đầu lúc|bắt đầu|lúc|vào|từ|bat dau luc|bat dau|luc|vao|tu)\s*\d{1,2}(?:(?::|g|h)\d{1,2})?\s*h?\s*(?:am|pm)?/gi, ' ')
    .replace(/(?:kết thúc lúc|kết thúc|đến|toi|den|ket thuc luc|ket thuc)\s*\d{1,2}(?:(?::|g|h)\d{1,2})?\s*h?\s*(?:am|pm)?/gi, ' ')
    .replace(/\b\d{1,2}(?:(?::|g|h)\d{1,2})?\s*h?\s*(?:am|pm)?\b/gi, ' ')
    .replace(/\b(trong|khoảng|khoang|kéo dài|keo dai)\s*\d+\s*(phút|phut|giờ|gio|tiếng|tieng|h)\b/gi, ' ')
    .replace(/\b(nửa tiếng|nua tieng|buổi sáng|buổi chiều|buổi tối|sáng|chiều|tối|trưa|sang|chieu|toi|trua|luc|ngay)\b/gi, ' ')
    .replace(/[,:-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

let summary = structuredSummary;
let start = structuredStart;
let end = structuredEnd;
let description = structuredDescription;
let location = structuredLocation;
let isReady = Boolean(summary && start && end);

if (!isReady) {
  const targetDate = parseTargetDate(text, now);
  let { startHour, startMinute, endHour, endMinute, durationMinutes } = parseTimeInfo(text);

  if (startHour !== null && endHour === null) {
    const startDate = new Date(buildIso(targetDate, startHour, startMinute));
    const endDate = new Date(startDate.getTime() + durationMinutes * 60000);
    endHour = endDate.getHours();
    endMinute = endDate.getMinutes();
  }

  if (startHour !== null && endHour !== null) {
    const startDate = new Date(buildIso(targetDate, startHour, startMinute));
    let endDate = new Date(buildIso(targetDate, endHour, endMinute));
    if (endDate.getTime() <= startDate.getTime() && endHour < 12) {
      endHour += 12;
      endDate = new Date(buildIso(targetDate, endHour, endMinute));
    }
  }

  summary = cleanupSummary(raw) || cleanupSummary(rawNormalized) || 'Lịch mới';
  isReady = startHour !== null && endHour !== null;
  start = isReady ? buildIso(targetDate, startHour, startMinute) : '';
  end = isReady ? buildIso(targetDate, endHour, endMinute) : '';
}

const guidance = '📅 <b>Tạo lịch</b>\n\nBạn hãy nhập theo mẫu như:\n- tạo lịch họp team lúc 15h mai\n- đặt lịch gặp khách 9:30-10:30 thứ 2 tuần sau\n- tạo lịch review lúc 14h, kết thúc 15h30\n- thêm lịch demo sản phẩm chiều mai 2 tiếng';

return [{
  json: {
    ...source,
    payload,
    message,
    rawText: raw,
    text,
    chatId,
    calendarId,
    summary,
    start,
    end,
    timezone: structuredTimezone || 'Asia/Ho_Chi_Minh',
    description,
    location,
    isReady,
    response: isReady ? '' : guidance
  }
}];
""",
    },
    ROOT / "google/docs/workflow_sub_google_docs_search_doc.json": {
        "Prepare Action": r"""
function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .trim();
}

function getTelegramContext(source) {
  const payload = source.payload || {};
  const message = source.message || payload.message || payload.body?.message || {};
  const chatId = source.chatId || message.chat?.id || payload.chatId || '';
  const rawText = String(
    source.rawText || source.text || message.text || message.caption || payload.text || ''
  ).trim();
  return { payload, message, chatId, rawText };
}

function cleanQuery(value) {
  return String(value || '')
    .trim()
    .replace(/^[\"'“”‘’]+|[\"'“”‘’]+$/g, '')
    .replace(/\s+/g, ' ');
}

const source = $('Execute Workflow Trigger').item.json || {};
const ctx = getTelegramContext(source);
const raw = ctx.rawText;
const text = normalize(raw);
const prefixes = ['tim doc', 'search doc', 'tim tai lieu'];
let body = raw;
for (const prefix of prefixes) {
  if (text.startsWith(prefix + ' ')) {
    body = raw.slice(prefix.length + 1).trim();
    break;
  }
}

const query = cleanQuery(source.query || source.docName || source.fileName || ctx.payload.query || ctx.payload.docName || body);
const limit = Number(source.limit || source.payload?.limit || 5) || 5;
const folderId = String(source.folderId || source.payload?.folderId || '').trim();

return [{
  json: {
    ...source,
    payload: ctx.payload,
    message: ctx.message,
    chatId: ctx.chatId,
    rawText: raw,
    text,
    query,
    folderId,
    limit,
    hasTarget: Boolean(query),
    response: query ? '' : '📝 <b>Tim Google Doc</b>\n\nVi du: <code>tim doc Project Plan</code>'
  }
}];
""",
    },
    ROOT / "google/drive/workflow_sub_google_drive_search_file.json": {
        "Prepare Action": r"""
const source = $('Execute Workflow Trigger').item.json || {};

const payload = source.payload || {};
const message =
  source.message ||
  payload.message ||
  payload.body?.message ||
  {};

const chatId =
  source.chatId ||
  message.chat?.id ||
  payload.chatId ||
  '';

const raw = String(
  source.rawText ||
  source.text ||
  message.text ||
  payload.text ||
  ''
).trim();

function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .trim();
}

function cleanQuery(value) {
  return String(value || '')
    .trim()
    .replace(/^["'“”‘’]+|["'“”‘’]+$/g, '')
    .replace(/\s+/g, ' ');
}

function extractSearchQuery(rawText) {
  const original = String(rawText || '').trim();
  const normalized = normalize(original);

  const prefixes = [
    'tim file',
    'search file',
    'kiem file',
    'tim trong drive',
    'find file',
    'tim tep',
    'kiem tep',
    'search drive',
    'drive search'
  ];

  for (const prefix of prefixes) {
    if (normalized.startsWith(prefix + ' ')) {
      return cleanQuery(original.slice(prefix.length + 1));
    }

    if (normalized === prefix) {
      return '';
    }
  }

  return '';
}

const query = cleanQuery(
  source.query ||
  source.fileName ||
  payload.query ||
  payload.fileName ||
  extractSearchQuery(raw)
);

const mimeType =
  source.mimeType ||
  payload.mimeType ||
  '';

const folderId =
  source.folderId ||
  payload.folderId ||
  'root';

const limit = Number(
  source.limit ||
  payload.limit ||
  5
) || 5;

return [{
  json: {
    ...source,
    payload,
    message,
    chatId,
    raw,
    rawText: raw,
    text: normalize(raw),
    query,
    fileName: query,
    mimeType,
    folderId,
    limit,
    hasTarget: Boolean(query),
    response: query
      ? ''
      : '📁 <b>Tìm file trong Drive</b>\n\nVí dụ: <code>tìm file hợp đồng</code>',
  },
}];
""",
    },
    ROOT / "google/sheets/workflow_sub_google_sheets_search_sheet.json": {
        "Prepare Action": r"""
function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .trim();
}

function getTelegramContext(source) {
  const payload = source.payload || {};
  const message = source.message || payload.message || payload.body?.message || {};
  const chatId = source.chatId || message.chat?.id || payload.chatId || '';
  const rawText = String(source.rawText || source.text || message.text || message.caption || payload.text || '' || payload.query || '').trim();
  return { payload, message, chatId, rawText };
}

function cleanQuery(value) {
  return String(value || '')
    .trim()
    .replace(/^[\"'“”‘’]+|[\"'“”‘’]+$/g, '')
    .replace(/\s+/g, ' ');
}

const source = $('Execute Workflow Trigger').item.json || {};
const ctx = getTelegramContext(source);
const raw = ctx.rawText;
const text = normalize(raw);
const prefixes = ['tim sheet', 'search sheet', 'tim bang tinh'];
let body = raw;
for (const prefix of prefixes) {
  if (text.startsWith(prefix + ' ')) {
    body = raw.slice(prefix.length + 1).trim();
    break;
  }
}

const query = cleanQuery(source.query || source.sheetName || source.fileName || ctx.payload.query || ctx.payload.sheetName || body);
const limit = Number(source.limit || source.payload?.limit || 5) || 5;
const folderId = String(source.folderId || source.payload?.folderId || '').trim();

return [{
  json: {
    ...source,
    payload: ctx.payload,
    message: ctx.message,
    chatId: ctx.chatId,
    rawText: raw,
    text,
    query,
    folderId,
    limit,
    hasTarget: Boolean(query),
    response: query ? '' : '📊 <b>Tim Google Sheet</b>\n\nVi du: <code>tim sheet Chi tieu</code>'
  }
}];
""",
    },
}


def main() -> None:
    for path, node_map in WORKFLOW_UPDATES.items():
        workflow = json.loads(path.read_text())
        for node in workflow["nodes"]:
            replacement = node_map.get(node["name"])
            if replacement is not None:
                node.setdefault("parameters", {})
                if isinstance(replacement, str):
                    node["parameters"]["jsCode"] = replacement.strip()
                else:
                    node["parameters"] = replacement
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {path}")


if __name__ == "__main__":
    main()
