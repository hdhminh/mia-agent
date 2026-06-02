#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/home/huynhminh/Projects/n8n")


PATCHES = {
    ROOT / "workflow_sub_weather.json": {
        "Tổng Hợp Thời Tiết": """const source = $('Chuẩn Bị Địa Điểm').item.json || {};
const raw = $json?.data ?? $json;
const data = typeof raw === 'string' ? JSON.parse(raw) : (raw || {});

const current = Array.isArray(data.current_condition) ? data.current_condition[0] || {} : {};
const today = Array.isArray(data.weather) ? data.weather[0] || {} : {};
const desc = String(current.weatherDesc?.[0]?.value || '').trim();
const tempC = current.temp_C || '';
const feelsLike = current.FeelsLikeC || '';
const humidity = current.humidity || '';
const windKmph = current.windspeedKmph || '';
const maxTemp = today.maxtempC || '';
const minTemp = today.mintempC || '';
const rainMm = current.precipMM || '';

const translateDesc = (value = '') => {
  const key = String(value).trim().toLowerCase();
  const dict = {
    clear: 'quang mây',
    sunny: 'nắng đẹp',
    'partly cloudy': 'có mây nhẹ',
    cloudy: 'nhiều mây',
    overcast: 'âm u',
    mist: 'có sương mỏng',
    fog: 'có sương mù',
    haze: 'trời hơi mờ',
    rain: 'có mưa',
    'light rain': 'mưa nhẹ',
    'moderate rain': 'mưa vừa',
    'heavy rain': 'mưa to',
    thunderstorm: 'có dông',
  };
  return dict[key] || key;
};

const location = String(source.location || 'đó').trim();
const parts = [];

if (desc) {
  parts.push(`Hiện tại ở ${location}, trời ${translateDesc(desc)}.`);
} else {
  parts.push(`Hiện tại ở ${location}, Mia đã lấy được thông tin thời tiết mới nhất.`);
}

if (tempC !== '') {
  let line = `Nhiệt độ khoảng ${tempC}°C`;
  if (feelsLike !== '') line += `, cảm giác như ${feelsLike}°C`;
  parts.push(`${line}.`);
}

const details = [];
if (humidity !== '') details.push(`độ ẩm ${humidity}%`);
if (windKmph !== '') details.push(`gió ${windKmph} km/h`);
if (rainMm !== '' && rainMm !== '0.0') details.push(`mưa ${rainMm} mm`);
if (minTemp !== '' || maxTemp !== '') details.push(`trong ngày dao động từ ${minTemp || '?'}°C đến ${maxTemp || '?'}°C`);
if (details.length) parts.push(`Mia ghi nhận ${details.join(', ')}.`);

return [{ json: { chatId: source.chatId || '', text: parts.join(' ').trim() } }];""",
    },
    ROOT / "workflow_sub_gold.json": {
        "Tổng Hợp Giá Vàng": """const source = $('Chuẩn bị ChatID').item.json || {};
const item = $input.item.json || {};

const updatedAt = String(item.updatedAt || item.updated_at || item.date || '').trim();
const buy = String(item.buy || item.mua_vao || item.buyPrice || '').trim();
const sell = String(item.sell || item.ban_ra || item.sellPrice || '').trim();

const formatMoney = (value = '') => {
  const digits = String(value).replace(/[^\\d]/g, '');
  if (!digits) return value;
  return `${Number(digits).toLocaleString('vi-VN')} đ/lượng`;
};

const parts = ['Mia vừa lấy giá vàng SJC 9999 mới nhất cho anh Minh.'];
if (updatedAt) parts.push(`Dữ liệu cập nhật lúc ${updatedAt}.`);
if (buy || sell) parts.push(`Hiện mua vào ${formatMoney(buy || 'chưa rõ')}, bán ra ${formatMoney(sell || 'chưa rõ')}.`);

return [{ json: { chatId: source.chatId || '', text: parts.join(' ').trim() } }];""",
    },
    ROOT / "workflow_sub_search.json": {
        "Tổng Hợp Kết Quả": """const source = $('Chuẩn Bị Query').item.json || {};
const html = String($json.data || '');

const decodeHtml = (value = '') => String(value)
  .replace(/&#x([0-9a-fA-F]+);/g, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
  .replace(/&#(\\d+);/g, (_, num) => String.fromCodePoint(parseInt(num, 10)))
  .replace(/&amp;/g, '&')
  .replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'")
  .replace(/&lt;/g, '<')
  .replace(/&gt;/g, '>');

const cleanText = (value = '') => decodeHtml(String(value).replace(/<[^>]+>/g, ' ').replace(/\\s+/g, ' ').trim());

const extractUrl = (href = '') => {
  const normalized = decodeHtml(href);
  const match = normalized.match(/[?&]uddg=([^&]+)/);
  if (match) {
    try {
      return decodeURIComponent(match[1]);
    } catch (error) {}
  }
  if (normalized.startsWith('//')) return `https:${normalized}`;
  return normalized;
};

const results = [];
const resultRegex = /<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>([\\s\\S]*?)<\\/a>/gi;
let match;
while ((match = resultRegex.exec(html)) !== null && results.length < 3) {
  const url = extractUrl(match[1]);
  const title = cleanText(match[2]);
  if (!url || !title) continue;
  if (results.some((item) => item.url === url)) continue;
  results.push({ url, title });
}

let text = `Mia thấy vài kết quả khá khớp với \"${source.query}\".`;
if (results.length > 0) {
  for (let i = 0; i < results.length; i += 1) {
    const item = results[i];
    text += `\\n- ${item.title}`;
  }
  text += '\\n\\nLink tham khảo:';
  for (let i = 0; i < results.length; i += 1) {
    const item = results[i];
    text += `\\n${i + 1}. ${item.url}`;
  }
} else {
  text += '\\nMia chưa thấy kết quả nào đủ rõ. Anh Minh thử đổi từ khóa cụ thể hơn nhé.';
}

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "workflow_sub_news.json": {
        "Format Tin Tức": """const staticData = $getWorkflowStaticData('global');
staticData.sentUrls = staticData.sentUrls || [];

let allItems = [];
let chatId = '';
let isAuto = false;

for (const [index, item] of $input.all().entries()) {
  const source = $('Chuẩn bị URL News').all()[index].json || {};
  chatId = source.chatId || '';
  isAuto = Boolean(source.isAuto);
  const topic = source.topic || 'Tin tức';
  let articles = item.json.rss?.channel?.item || [];
  if (!Array.isArray(articles)) articles = [articles];

  for (const article of articles) {
    if (!article.title || !article.link) continue;
    let pubDate = 0;
    try { pubDate = new Date(article.pubDate).getTime(); } catch (error) {}
    allItems.push({
      title: String(article.title).trim(),
      link: String(article.link).trim(),
      pubDate,
      topic,
    });
  }
}

allItems.sort((a, b) => b.pubDate - a.pubDate);

const finalItems = [];
for (const article of allItems) {
  if (isAuto && staticData.sentUrls.includes(article.link)) continue;
  finalItems.push(article);
  if (finalItems.length >= 3) break;
}

if (isAuto) {
  for (const article of finalItems) staticData.sentUrls.push(article.link);
  if (staticData.sentUrls.length > 200) staticData.sentUrls = staticData.sentUrls.slice(-200);
}

if (finalItems.length === 0) {
  return [{ json: { text: 'Hiện chưa có bài mới nổi bật để Mia gửi anh Minh.', chatId } }];
}

const topicLine = [...new Set(finalItems.map((item) => item.topic))].slice(0, 2).join(', ');
let text = topicLine ? `Mia điểm nhanh vài tin nổi bật về ${topicLine}:` : 'Mia điểm nhanh vài tin nổi bật cho anh Minh:';

for (let i = 0; i < finalItems.length; i += 1) {
  const item = finalItems[i];
  text += `\\n- ${item.title}`;
}

text += '\\n\\nĐọc thêm:';
for (let i = 0; i < finalItems.length; i += 1) {
  const item = finalItems[i];
  text += `\\n${i + 1}. ${item.link}`;
}

return [{ json: { text: text.trim(), chatId } }];""",
    },
    ROOT / "google/gmail/workflow_sub_google_gmail_list_inbox.json": {
        "Format Danh Sach Email": """const source = $('Chuan Bi List Inbox').item.json;

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
  const normalized = /^\\d+$/.test(String(value)) ? Number(value) : value;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh' });
};

const hasUnreadLabel = (email) => {
  const labels = Array.isArray(email.labelIds) ? email.labelIds : [];
  const richLabels = Array.isArray(email.labels) ? email.labels : [];
  return labels.includes('UNREAD') || richLabels.some((label) => label?.id === 'UNREAD' || label?.name === 'UNREAD');
};

const buildMailLink = (email) => {
  const threadId = pickFirst(email.threadId);
  const messageId = pickFirst(email.id);
  if (threadId) return `https://mail.google.com/mail/u/0/#inbox/${threadId}`;
  if (messageId) return `https://mail.google.com/mail/u/0/#inbox/${messageId}`;
  return '';
};

const rows = $input.all()
  .map((item) => item.json || {})
  .filter((email) => email && Object.keys(email).length > 0 && (email.id || email.subject || email.Subject || email.from || email.From || email.snippet))
  .slice(0, 3);

let text = '';

if (rows.length === 0) {
  text = 'Hộp thư của anh Minh hiện không có email mới đáng chú ý.';
} else {
  text = `Anh Minh đang có ${rows.length} email đáng chú ý gần đây:`;
  const links = [];

  for (let i = 0; i < rows.length; i++) {
    const email = rows[i];
    const subject = pickFirst(email.subject, email.Subject, email.payload?.headers?.find((h) => h.name === 'Subject')?.value) || 'Không có tiêu đề';
    const from = pickFirst(email.from?.value?.[0]?.name, email.from?.value?.[0]?.address, email.From, email.from, email.payload?.headers?.find((h) => h.name === 'From')?.value) || 'Không rõ người gửi';
    const date = formatDate(pickFirst(email.date, email.Date, email.internalDate));
    const link = buildMailLink(email);
    const unread = hasUnreadLabel(email) ? 'chưa đọc' : 'đã đọc';

    text += `\\n${i + 1}. ${subject} — từ ${from}`;
    if (date) text += `, lúc ${date}`;
    text += ` (${unread})`;
    if (link && !links.includes(link)) links.push(link);
  }

  if (links.length) {
    text += '\\n\\nMở nhanh email:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}

return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/calendar/workflow_sub_google_calendar_list_today.json": {
        "Format Danh Sach Lich": """function toDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
function formatDate(date) {
  return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: 'numeric' }).format(date);
}
function formatTime(date) {
  return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hour12: false }).format(date);
}
function formatRange(startValue, endValue) {
  const startDate = toDate(startValue);
  const endDate = toDate(endValue);
  if (!startDate) return startValue || '';
  if (!endDate) return `${formatTime(startDate)}, ${formatDate(startDate)}`;
  const sameDay = startDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }) === endDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
  if (sameDay) return `${formatTime(startDate)} - ${formatTime(endDate)}, ${formatDate(startDate)}`;
  return `${formatTime(startDate)}, ${formatDate(startDate)} → ${formatTime(endDate)}, ${formatDate(endDate)}`;
}
const source = $('Chuan Bi Lich Hom Nay').item.json;
const rows = $input.all().map(item => item.json || {}).filter((event) => event && Object.keys(event).length > 0 && (event.id || event.summary || event.start || event.end)).slice(0, 3);
let text = '';
if (rows.length === 0) {
  text = 'Hôm nay anh Minh chưa có lịch nào cả.';
} else {
  text = 'Hôm nay anh Minh có mấy lịch như sau:';
  const links = [];
  for (let i = 0; i < rows.length; i++) {
    const event = rows[i];
    const title = event.summary || 'Không có tiêu đề';
    const start = event.start?.dateTime || event.start?.date || '';
    const end = event.end?.dateTime || event.end?.date || '';
    const link = event.htmlLink || '';
    text += `\\n${i + 1}. ${title} — ${formatRange(start, end)}`;
    if (link) links.push(link);
  }
  if (links.length) {
    text += '\\n\\nMở nhanh lịch:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}
return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/calendar/workflow_sub_google_calendar_list_tomorrow.json": {
        "Format Danh Sach Lich": """function toDate(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
function formatDate(date) {
  return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', day: '2-digit', month: '2-digit', year: 'numeric' }).format(date);
}
function formatTime(date) {
  return new Intl.DateTimeFormat('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour: '2-digit', minute: '2-digit', hour12: false }).format(date);
}
function formatRange(startValue, endValue) {
  const startDate = toDate(startValue);
  const endDate = toDate(endValue);
  if (!startDate) return startValue || '';
  if (!endDate) return `${formatTime(startDate)}, ${formatDate(startDate)}`;
  const sameDay = startDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' }) === endDate.toLocaleDateString('en-CA', { timeZone: 'Asia/Ho_Chi_Minh' });
  if (sameDay) return `${formatTime(startDate)} - ${formatTime(endDate)}, ${formatDate(startDate)}`;
  return `${formatTime(startDate)}, ${formatDate(startDate)} → ${formatTime(endDate)}, ${formatDate(endDate)}`;
}
const source = $('Chuan Bi Lich Ngay Mai').item.json;
const rows = $input.all().map(item => item.json || {}).filter((event) => event && Object.keys(event).length > 0 && (event.id || event.summary || event.start || event.end)).slice(0, 3);
let text = '';
if (rows.length === 0) {
  text = 'Ngày mai anh Minh chưa có lịch nào cả.';
} else {
  text = 'Ngày mai anh Minh có mấy lịch như sau:';
  const links = [];
  for (let i = 0; i < rows.length; i++) {
    const event = rows[i];
    const title = event.summary || 'Không có tiêu đề';
    const start = event.start?.dateTime || event.start?.date || '';
    const end = event.end?.dateTime || event.end?.date || '';
    const link = event.htmlLink || '';
    text += `\\n${i + 1}. ${title} — ${formatRange(start, end)}`;
    if (link) links.push(link);
  }
  if (links.length) {
    text += '\\n\\nMở nhanh lịch:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}
return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/docs/workflow_sub_google_docs_search_doc.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const rows = $input.all().map((item) => item.json || {}).filter((item) => item.id || item.name).slice(0, 3);
const query = source.query || '';

let text = '';
if (!rows.length) {
  text = query
    ? `Mia chưa thấy tài liệu nào thật sự khớp với từ khóa \"${query}\".`
    : 'Mia chưa tìm thấy tài liệu phù hợp.';
} else {
  text = query
    ? `Mia tìm thấy ${rows.length} tài liệu khá khớp với từ khóa \"${query}\":`
    : `Mia tìm thấy ${rows.length} tài liệu phù hợp:`;
  const links = [];
  rows.forEach((doc, index) => {
    const name = doc.name || 'Không rõ tên';
    const link = doc.webViewLink || (doc.id ? `https://docs.google.com/document/d/${doc.id}/edit` : '');
    const modified = doc.modifiedTime ? new Date(doc.modifiedTime).toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false }) : '';
    text += `\\n${index + 1}. ${name}`;
    if (modified) text += ` — sửa lúc ${modified}`;
    if (link) links.push(link);
  });
  if (links.length) {
    text += '\\n\\nMở tài liệu:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}

return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/drive/workflow_sub_google_drive_list_files.json": {
        "Format Danh Sach File": """const pickFirst = (...values) => {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
};

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        hour12: false,
      });
};

const getFileType = (mimeType = '') => {
  if (mimeType === 'application/vnd.google-apps.folder') return 'folder';
  if (mimeType === 'application/vnd.google-apps.document') return 'Google Docs';
  if (mimeType === 'application/vnd.google-apps.spreadsheet') return 'Google Sheets';
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.startsWith('image/')) return 'ảnh';
  return 'file';
};

const source = $('Chuan Bi List Files').item.json;
const rows = $input.all().map((item) => item.json || {}).filter((item) => item.id || item.name).slice(0, 3);

let text = '';
if (!rows.length) {
  text = 'Trong Drive hiện chưa có file nào nổi bật để Mia liệt kê.';
} else {
  text = `Mia thấy ${rows.length} file gần đây trong Drive:`;
  const links = [];
  rows.forEach((file, index) => {
    const name = file.name || 'Không rõ tên';
    const link = pickFirst(file.webViewLink);
    const modified = formatDate(file.modifiedTime || file.createdTime);
    const fileType = getFileType(file.mimeType || '');
    text += `\\n${index + 1}. ${name}`;
    if (fileType) text += ` — ${fileType}`;
    if (modified) text += `, cập nhật ${modified}`;
    if (link) links.push(link);
  });
  if (links.length) {
    text += '\\n\\nMở file:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}

return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/drive/workflow_sub_google_drive_search_file.json": {
        "Format Action": """const pickFirst = (...values) => {
  for (const value of values) {
    if (value === undefined || value === null) continue;
    if (typeof value === 'string' && value.trim()) return value.trim();
    if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  }
  return '';
};

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ''
    : date.toLocaleString('vi-VN', {
        timeZone: 'Asia/Ho_Chi_Minh',
        hour12: false,
      });
};

const getFileType = (mimeType = '') => {
  if (mimeType === 'application/vnd.google-apps.folder') return 'folder';
  if (mimeType === 'application/vnd.google-apps.document') return 'Google Docs';
  if (mimeType === 'application/vnd.google-apps.spreadsheet') return 'Google Sheets';
  if (mimeType === 'application/pdf') return 'PDF';
  if (mimeType.startsWith('image/')) return 'ảnh';
  return 'file';
};

const source = $('Prepare Action').item.json;

const rows = $input
  .all()
  .map((item) => item.json || {})
  .filter((item) => item.id || item.name)
  .sort((a, b) => {
    const timeA = new Date(a.modifiedTime || a.createdTime || 0).getTime();
    const timeB = new Date(b.modifiedTime || b.createdTime || 0).getTime();
    return timeB - timeA;
  })
  .slice(0, 3);

const query = pickFirst(source.query, source.fileName, source.rawText, source.text);

let text = '';
if (!rows.length) {
  text = query
    ? `Mia chưa tìm thấy file nào thật sự khớp với \"${query}\".`
    : 'Mia chưa tìm thấy file phù hợp.';
} else {
  text = query
    ? `Mia tìm thấy ${rows.length} file khá khớp với \"${query}\":`
    : `Mia tìm thấy ${rows.length} file phù hợp:`;
  const links = [];
  rows.forEach((file, index) => {
    const name = file.name || 'Không rõ tên';
    const link = pickFirst(file.webViewLink);
    const modified = formatDate(file.modifiedTime || file.createdTime);
    const fileType = getFileType(file.mimeType || '');
    text += `\\n${index + 1}. ${name}`;
    if (fileType) text += ` — ${fileType}`;
    if (modified) text += `, cập nhật ${modified}`;
    if (link) links.push(link);
  });
  if (links.length) {
    text += '\\n\\nMở file:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}

return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "google/sheets/workflow_sub_google_sheets_search_sheet.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const rows = $input.all().map((item) => item.json || {}).filter((item) => item.id || item.name).slice(0, 3);
const query = source.query || '';

let text = '';
if (!rows.length) {
  text = query
    ? `Mia chưa tìm thấy bảng tính nào thật sự khớp với \"${query}\".`
    : 'Mia chưa tìm thấy bảng tính phù hợp.';
} else {
  text = query
    ? `Mia tìm thấy ${rows.length} bảng tính khá khớp với \"${query}\":`
    : `Mia tìm thấy ${rows.length} bảng tính phù hợp:`;
  const links = [];
  rows.forEach((sheet, index) => {
    const name = sheet.name || 'Không rõ tên';
    const link = sheet.webViewLink || (sheet.id ? `https://docs.google.com/spreadsheets/d/${sheet.id}/edit` : '');
    const modified = sheet.modifiedTime
      ? new Date(sheet.modifiedTime).toLocaleString('vi-VN', {
          timeZone: 'Asia/Ho_Chi_Minh',
          hour12: false,
        })
      : '';
    text += `\\n${index + 1}. ${name}`;
    if (modified) text += ` — cập nhật ${modified}`;
    if (link) links.push(link);
  });
  if (links.length) {
    text += '\\n\\nMở bảng tính:';
    links.slice(0, 3).forEach((link, index) => {
      text += `\\n${index + 1}. ${link}`;
    });
  }
}

return [{ json: { chatId: source.chatId, text: text.trim() } }];""",
    },
    ROOT / "shortlink/workflow_shortlink_create.json": {
        "Format Success Response": """const source = $('Decide Final Record').item.json || $('Prepare Shortlink Request').item.json || {};
const row = $input.item.json || {};

const shortUrl = row.short_url || source.shortUrl || '';
const longUrl = row.long_url || source.longUrl || '';
const expiresAt = row.expires_at ? new Date(row.expires_at) : null;
const expiresAtDisplay = expiresAt
  ? expiresAt.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false })
  : source.expiresAtDisplay || 'vĩnh viễn';

let text = 'Mia đã rút gọn link xong rồi anh Minh.';
if (shortUrl) text += `\\nLink ngắn: ${shortUrl}`;
if (expiresAtDisplay) text += `\\nHết hạn: ${expiresAtDisplay}`;
if (longUrl) text += `\\nLink gốc: ${longUrl}`;
if (source.clampMessage) text += `\\nLưu ý: ${source.clampMessage}`;

return [{ json: {
  chatId: source.chatId || '',
  text,
  result: {
    id: row.id || source.id || '',
    short_url: shortUrl,
    long_url: longUrl,
    host: row.host || source.host || '',
    expires_at: row.expires_at || source.expiresAtIso || null,
    expires_at_display: expiresAtDisplay,
    requested_ttl: source.requestedTtlLabel || '',
    effective_ttl: source.effectiveTtlLabel || ''
  }
} }];""",
    },
}


def patch_workflow(path: Path, node_patches: dict[str, str]) -> None:
    data = json.loads(path.read_text())
    changed = False
    for node in data.get("nodes", []):
        replacement = node_patches.get(node.get("name", ""))
        if replacement is None:
            continue
        if node.get("parameters", {}).get("jsCode") != replacement:
            node.setdefault("parameters", {})["jsCode"] = replacement
            changed = True
    if changed:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print(f"patched {path}")


def main() -> None:
    for path, node_patches in PATCHES.items():
        patch_workflow(path, node_patches)


if __name__ == "__main__":
    main()
