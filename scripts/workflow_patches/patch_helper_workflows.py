#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/home/huynhminh/Projects/n8n")

WORKFLOWS = [
    ROOT / "workflow_sub_weather.json",
    ROOT / "workflow_sub_gold.json",
    ROOT / "workflow_sub_news.json",
    ROOT / "workflow_sub_search.json",
    ROOT / "google/calendar/workflow_sub_google_calendar_master.json",
    ROOT / "google/gmail/workflow_sub_google_gmail_master.json",
    ROOT / "google/drive/workflow_sub_google_drive_master.json",
    ROOT / "google/docs/workflow_sub_google_docs_master.json",
    ROOT / "google/sheets/workflow_sub_google_sheets_master.json",
    ROOT / "shortlink/workflow_shortlink_create.json",
]

NORMALIZE_TOOL_TEXT_CODE = """const source = $input.item.json || {};

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
    .replace(/<br\\s*\\/?>/gi, '\\n')
    .replace(/<\\/p>/gi, '\\n\\n')
    .replace(/<\\/div>/gi, '\\n')
    .replace(/<\\/li>/gi, '\\n')
    .replace(/<li>/gi, '- ')
    .replace(/<\\/h\\d>/gi, '\\n')
    .replace(/<a[^>]*href="([^"]+)"[^>]*>(.*?)<\\/a>/gi, '$2 ($1)')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[ \\t]+/g, ' ')
    .replace(/\\n\\s+/g, '\\n')
    .replace(/\\n{3,}/g, '\\n\\n')
    .trim();
}

const rawText = String(
  source.text ||
  source.responseText ||
  source.output ||
  source.response ||
  ''
).trim();

const plainText = String(source.plainText || htmlToPlainText(rawText)).trim();

return [{
  json: {
    ...source,
    text: plainText || rawText
  }
}];"""

BOOL_CHAT_CONDITION = {
    "conditions": {
        "boolean": [
            {
                "value1": "={{ !!String($json.chatId || '').trim() }}",
                "value2": True,
            }
        ]
    }
}

WEATHER_PREP_CODE = """const payload = $('Execute Workflow Trigger').item.json || {};
const args = payload.payload?.args || payload.args || {};
const msg = payload.message || payload.body?.message || payload || {};

const chatId = String(payload.chatId || msg.chat?.id || '').trim();
const rawText = String(msg.text || payload.text || payload.query || '').trim();

let location = String(args.location || '').trim();
if (!location) {
  location = rawText
    .replace(/^(thoi tiet|thời tiết|weather|nhiet do|nhiệt độ|troi|trời|du bao thoi tiet|dự báo thời tiết)\\s*/i, '')
    .replace(/^(tai|tại|o|ở|cho|cho toi|cho tôi|hom nay|hôm nay)\\s*/i, '')
    .trim();
}

if (!location) location = 'Ho Chi Minh City';

return [{ json: { chatId, rawText, location } }];"""

WEATHER_FORMAT_CODE = """const source = $('Chuẩn Bị Địa Điểm').item.json || {};
const raw = $json?.data ?? $json;
const data = typeof raw === 'string' ? JSON.parse(raw) : (raw || {});

const current = Array.isArray(data.current_condition) ? data.current_condition[0] || {} : {};
const today = Array.isArray(data.weather) ? data.weather[0] || {} : {};
const nearest = Array.isArray(data.nearest_area) ? data.nearest_area[0] || {} : {};
const request = Array.isArray(data.request) ? data.request[0] || {} : {};

const areaName = nearest.areaName?.[0]?.value || source.location;
const region = nearest.region?.[0]?.value || '';
const country = nearest.country?.[0]?.value || '';
const desc = current.weatherDesc?.[0]?.value || '';
const tempC = current.temp_C || '';
const feelsLike = current.FeelsLikeC || '';
const humidity = current.humidity || '';
const windKmph = current.windspeedKmph || '';
const maxTemp = today.maxtempC || '';
const minTemp = today.mintempC || '';
const rainMm = current.precipMM || '';
const sunrise = today.astronomy?.[0]?.sunrise || '';
const sunset = today.astronomy?.[0]?.sunset || '';

let locationLine = request.query || areaName || source.location;
if (region && !locationLine.includes(region)) locationLine += `, ${region}`;
if (country && !locationLine.includes(country)) locationLine += `, ${country}`;

const parts = [];
parts.push(`Thời tiết tại ${locationLine}:`);

if (tempC !== '') {
  let tempLine = `- Nhiệt độ: ${tempC}°C`;
  if (feelsLike !== '') tempLine += `, cảm giác như ${feelsLike}°C`;
  parts.push(tempLine);
}
if (desc) parts.push(`- Tình trạng: ${desc}`);
if (humidity !== '') parts.push(`- Độ ẩm: ${humidity}%`);
if (windKmph !== '') parts.push(`- Gió: ${windKmph} km/h`);
if (rainMm !== '') parts.push(`- Lượng mưa: ${rainMm} mm`);
if (minTemp !== '' || maxTemp !== '') parts.push(`- Nhiệt độ trong ngày: ${minTemp}°C đến ${maxTemp}°C`);
if (sunrise || sunset) parts.push(`- Mặt trời: ${sunrise || '?'} / ${sunset || '?'}`);

if (parts.length === 1) {
  parts[0] = `Không lấy được dữ liệu thời tiết cho ${source.location}. Bạn thử ghi rõ địa điểm hơn nhé.`;
}

return [{ json: { chatId: source.chatId || '', text: parts.join('\\n').trim() } }];"""

SEARCH_PREP_CODE = """const payload = $('Execute Workflow Trigger').item.json || {};
const args = payload.payload?.args || payload.args || {};
const msg = payload.message || payload.body?.message || payload || {};

const chatId = String(payload.chatId || msg.chat?.id || '').trim();
const rawText = String(msg.text || payload.text || payload.query || '').trim();

let query = String(args.query || '').trim();
if (!query) {
  query = rawText
    .replace(/^(tim|tìm|tim kiem|tìm kiếm|timkiem|search|tra cuu|tra cứu|google|duckduckgo)\\s*/i, '')
    .replace(/^(ve|về|thong tin ve|thông tin về|cho toi biet ve|cho tôi biết về|noi ve|nói về)\\s*/i, '')
    .trim();
}

if (!query) query = 'n8n automation';

return [{ json: { chatId, query, rawText } }];"""

SEARCH_FORMAT_CODE = """const source = $('Chuẩn Bị Query').item.json || {};
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
while ((match = resultRegex.exec(html)) !== null && results.length < 5) {
  const url = extractUrl(match[1]);
  const title = cleanText(match[2]);
  if (!url || !title) continue;
  results.push({ url, title });
}

let text = `Kết quả tìm kiếm cho: ${source.query}`;
if (results.length > 0) {
  text += '\\n';
  for (let i = 0; i < results.length; i += 1) {
    const item = results[i];
    text += `\\n${i + 1}. ${item.title}\\n${item.url}`;
  }
} else {
  text += '\\nChưa tìm thấy kết quả rõ ràng. Bạn thử đổi từ khóa cụ thể hơn nhé.';
}

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];"""

NEWS_CODE = """const source = $input.item.json || {};
const args = source.payload?.args || source.args || {};
const msg = source.message || source.body?.message || {};
const directChatId = String(source.chatId || msg.chat?.id || '').trim();
const deliveryMode = String(source.deliveryMode || source.payload?.deliveryMode || '').trim().toLowerCase();
const scheduledFallbackChatId = String($env.TELEGRAM_ADMIN_CHAT_ID || '').trim();
const rawText = String(msg.text || source.text || source.rawText || source.query || '').trim();
const normalizedText = rawText
  .toLowerCase()
  .normalize('NFD')
  .replace(/[\\u0300-\\u036f]/g, '')
  .replace(/đ/g, 'd');
const explicitTopic = String(args.topic || '').trim();

let chatId = '';
let isAuto = false;

if (directChatId) {
  chatId = directChatId;
} else if (deliveryMode === 'return') {
  chatId = '';
} else {
  chatId = scheduledFallbackChatId;
  isAuto = Boolean(chatId);
}

let topics = [];
if (explicitTopic) {
  topics = [explicitTopic];
} else if (isAuto) {
  topics = ['kinh-doanh', 'the-gioi', 'so-hoa'];
} else {
  if (normalizedText.includes('kinhdoanh') || normalizedText.includes('business')) topics.push('kinh-doanh');
  if (normalizedText.includes('thegioi') || normalizedText.includes('world')) topics.push('the-gioi');
  if (normalizedText.includes('congnghe') || normalizedText.includes('tech') || normalizedText.includes('sohoa')) topics.push('so-hoa');
  if (normalizedText.includes('thoisu') || normalizedText.includes('news')) topics.push('thoi-su');
  if (normalizedText.includes('suckhoe') || normalizedText.includes('health')) topics.push('suc-khoe');
  if (normalizedText.includes('thethao') || normalizedText.includes('sport')) topics.push('the-thao');
  if (normalizedText.includes('giaitri') || normalizedText.includes('entertainment')) topics.push('giai-tri');
  if (normalizedText.includes('phapluat') || normalizedText.includes('law')) topics.push('phap-luat');
  if (normalizedText.includes('giaoduc') || normalizedText.includes('education')) topics.push('giao-duc');
  if (normalizedText.includes('doisong') || normalizedText.includes('life')) topics.push('doi-song');
  if (normalizedText.includes('xe') || normalizedText.includes('car')) topics.push('xe');
  if (normalizedText.includes('dulich') || normalizedText.includes('travel')) topics.push('du-lich');
  if (normalizedText.includes('khoahoc') || normalizedText.includes('science')) topics.push('khoa-hoc');

  if (topics.length === 0) topics = ['kinh-doanh', 'the-gioi', 'so-hoa'];
}

const topicNames = {
  'kinh-doanh': 'Kinh doanh', 'the-gioi': 'Thế giới', 'so-hoa': 'Công nghệ',
  'thoi-su': 'Thời sự', 'suc-khoe': 'Sức khỏe', 'the-thao': 'Thể thao',
  'giai-tri': 'Giải trí', 'phap-luat': 'Pháp luật', 'giao-duc': 'Giáo dục',
  'doi-song': 'Đời sống', 'xe': 'Xe', 'du-lich': 'Du lịch', 'khoa-hoc': 'Khoa học'
};

const feedMap = {
  'kinh-doanh': 'https://vnexpress.net/rss/kinh-doanh.rss',
  'the-gioi': 'https://vnexpress.net/rss/the-gioi.rss',
  'so-hoa': 'https://vnexpress.net/rss/so-hoa.rss',
  'thoi-su': 'https://vnexpress.net/rss/thoi-su.rss',
  'suc-khoe': 'https://vnexpress.net/rss/suc-khoe.rss',
  'the-thao': 'https://vnexpress.net/rss/the-thao.rss',
  'giai-tri': 'https://vnexpress.net/rss/giai-tri.rss',
  'phap-luat': 'https://vnexpress.net/rss/phap-luat.rss',
  'giao-duc': 'https://vnexpress.net/rss/giao-duc.rss',
  'doi-song': 'https://vnexpress.net/rss/doi-song.rss',
  'xe': 'https://vnexpress.net/rss/oto-xe-may.rss',
  'du-lich': 'https://vnexpress.net/rss/du-lich.rss',
  'khoa-hoc': 'https://vnexpress.net/rss/khoa-hoc.rss'
};

return topics.map((topic) => ({
  json: {
    ...source,
    chatId,
    isAuto,
    text: rawText,
    rawText,
    topic,
    url: feedMap[topic] || feedMap['kinh-doanh'],
    topics,
    topicNames,
    feedMap
  }
}));"""

NEWS_FORMAT_CODE = """const staticData = $getWorkflowStaticData('global');
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
  if (finalItems.length >= 5) break;
}

if (isAuto) {
  for (const article of finalItems) staticData.sentUrls.push(article.link);
  if (staticData.sentUrls.length > 200) staticData.sentUrls = staticData.sentUrls.slice(-200);
}

if (finalItems.length === 0) {
  return [{ json: { text: 'Hiện chưa có bài mới để gửi.', chatId } }];
}

const topicLine = [...new Set(finalItems.map((item) => item.topic))].slice(0, 3).join(', ');
let text = topicLine ? `Tin nổi bật: ${topicLine}` : 'Tin nổi bật';

for (let i = 0; i < finalItems.length; i += 1) {
  const item = finalItems[i];
  text += `\\n\\n${i + 1}. [${item.topic}] ${item.title}\\n${item.link}`;
}

return [{ json: { text: text.trim(), chatId } }];"""

GOLD_CHAT_CODE = """const source = $input.item.json || {};
const msg = source.message || source.body?.message || {};
const directChatId = String(source.chatId || msg.chat?.id || '').trim();
const deliveryMode = String(source.deliveryMode || source.payload?.deliveryMode || '').trim().toLowerCase();
const scheduledFallbackChatId = String($env.TELEGRAM_ADMIN_CHAT_ID || '').trim();

let chatId = '';
let isAuto = false;

if (directChatId) {
  chatId = directChatId;
} else if (deliveryMode === 'return') {
  chatId = '';
} else {
  chatId = scheduledFallbackChatId;
  isAuto = Boolean(chatId);
}

return [{ json: { ...source, chatId, isAuto } }];"""

GOLD_FORMAT_CODE = """const source = $('Chuẩn bị ChatID').item.json || {};
const data = $json || {};

const formatPrice = (value) => {
  const amount = Number(value || 0);
  if (!Number.isFinite(amount) || amount <= 0) return 'N/A';
  return `${amount.toLocaleString('vi-VN')} đ/lượng`;
};

let text = 'Không lấy được giá vàng lúc này. Bạn thử lại sau nhé.';
if (data.success) {
  const title = data.name || 'SJC 9999';
  const dateLine = [data.date, data.time].filter(Boolean).join(' ');
  text = `Giá vàng ${title}`;
  if (dateLine) text += `\\nCập nhật: ${dateLine}`;
  text += `\\n- Mua vào: ${formatPrice(data.buy)}`;
  text += `\\n- Bán ra: ${formatPrice(data.sell)}`;
}

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];"""

SHORTLINK_PREP_CODE = """const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const args = payload.args || source.args || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';
const deliveryMode = String(source.deliveryMode || payload.deliveryMode || (chatId ? 'telegram' : 'return')).trim() || 'return';
const rawText = String(source.rawText || source.text || message.text || message.caption || payload.text || payload.query || '').trim();

function normalize(str) {
  return String(str || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\\u0300-\\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .trim();
}

function escapeSql(value = '') {
  return String(value || '').replace(/'/g, "''");
}

function parseDuration(value) {
  const text = normalize(value);
  if (!text) return null;
  if (/\\b(vinh vien|khong het han|forever)\\b/.test(text)) {
    return { forever: true, ms: null, label: 'vĩnh viễn' };
  }
  const compact = text.match(/(\\d+)\\s*(h|d)\\b/);
  if (compact) {
    const amount = Number(compact[1]);
    const unit = compact[2];
    if (unit === 'h') return { forever: false, ms: amount * 3600 * 1000, label: `${amount}h` };
    if (unit === 'd') return { forever: false, ms: amount * 24 * 3600 * 1000, label: `${amount}d` };
  }
  const verbose = text.match(/(\\d+)\\s*(gio|ngay|tuan|thang|hour|day|week|month)\\b/);
  if (verbose) {
    const amount = Number(verbose[1]);
    const unit = verbose[2];
    if (unit === 'gio' || unit === 'hour') return { forever: false, ms: amount * 3600 * 1000, label: `${amount} giờ` };
    if (unit === 'ngay' || unit === 'day') return { forever: false, ms: amount * 24 * 3600 * 1000, label: `${amount} ngày` };
    if (unit === 'tuan' || unit === 'week') return { forever: false, ms: amount * 7 * 24 * 3600 * 1000, label: `${amount} tuần` };
    if (unit === 'thang' || unit === 'month') return { forever: false, ms: amount * 30 * 24 * 3600 * 1000, label: `${amount} tháng` };
  }
  return null;
}

function safeParseHttpUrl(value) {
  const input = String(value || '').trim();
  if (!input) return null;
  if (typeof URL === 'function') {
    try {
      const parsed = new URL(input);
      const protocol = String(parsed.protocol || '').toLowerCase();
      if (protocol !== 'http:' && protocol !== 'https:') return null;
      if (!parsed.hostname) return null;
      return {
        href: parsed.toString(),
        host: parsed.host,
        hostname: parsed.hostname,
        protocol,
      };
    } catch (error) {}
  }
  const match = input.match(/^(https?):\\/\\/([^\\s/?#]+)([^\\s]*)?$/i);
  if (!match) return null;
  const protocol = `${match[1].toLowerCase()}:`;
  const host = match[2];
  const path = match[3] || '';
  const hostname = host.replace(/:\\d+$/, '');
  if (!hostname) return null;
  return {
    href: `${protocol}//${host}${path}`,
    host,
    hostname: hostname.toLowerCase(),
    protocol,
  };
}

function isPrivateHost(hostname) {
  const host = String(hostname || '').toLowerCase();
  if (!host) return true;
  if (host === 'localhost' || host === '0.0.0.0' || host === '127.0.0.1' || host === '::1') return true;
  if (host.endsWith('.local')) return true;
  if (/^10\\./.test(host)) return true;
  if (/^192\\.168\\./.test(host)) return true;
  if (/^172\\.(1[6-9]|2\\d|3[0-1])\\./.test(host)) return true;
  return false;
}

function hashHex(input) {
  let h1 = 0xdeadbeef ^ input.length;
  let h2 = 0x41c6ce57 ^ input.length;
  for (let index = 0; index < input.length; index += 1) {
    const codePoint = input.charCodeAt(index);
    h1 = Math.imul(h1 ^ codePoint, 2654435761);
    h2 = Math.imul(h2 ^ codePoint, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return `${(h2 >>> 0).toString(16).padStart(8, '0')}${(h1 >>> 0).toString(16).padStart(8, '0')}`;
}

const helpText = [
  'Mia có thể rút gọn link như sau:',
  '- rút gọn link https://example.com',
  '- rút gọn link https://example.com trong 7 ngày',
  '- short link https://example.com 24h',
  '- tạo link ngắn https://example.com vĩnh viễn',
  '',
  'Mặc định link sống 30 ngày.',
  'Hỗ trợ TTL: 1h, 24h, 7d, 30d, 1 tuần, 1 tháng, vĩnh viễn.',
].join('\\n');

const normalized = normalize(rawText);
const argUrl = String(args.url || '').trim();
const argTtl = String(args.ttl || '').trim();

if ((!rawText && !argUrl) || /\\b(shortlink help|short link help|help shortlink|huong dan shortlink)\\b/.test(normalized)) {
  return [{ json: { chatId, deliveryMode, ok: false, responseText: helpText } }];
}

const rawUrl = argUrl || String((rawText.match(/https?:\\/\\/[^\\s<>"']+/i) || [])[0] || '').replace(/[),.;!?]+$/, '').trim();
if (!rawUrl) {
  return [{ json: { chatId, deliveryMode, ok: false, responseText: 'Thiếu URL. Ví dụ: rút gọn link https://example.com trong 7 ngày.' } }];
}

const parsedUrl = safeParseHttpUrl(rawUrl);
if (!parsedUrl) {
  return [{ json: { chatId, deliveryMode, ok: false, responseText: 'URL không hợp lệ. Chỉ nhận http:// hoặc https://.' } }];
}

const allowLocal = String($env.SHORTLINK_ALLOW_LOCAL || 'false').toLowerCase() === 'true';
if (!allowLocal && isPrivateHost(parsedUrl.hostname)) {
  return [{ json: { chatId, deliveryMode, ok: false, responseText: 'Không cho phép URL nội bộ hoặc local.' } }];
}

const ttlSource = argTtl || rawText.replace(rawUrl, ' ').trim();
const requestedTtl = parseDuration(ttlSource);
const defaultTtl = parseDuration($env.SHORTLINK_DEFAULT_TTL || '30d') || { forever: false, ms: 30 * 24 * 3600 * 1000, label: '30d' };
const maxDays = Number($env.SHORTLINK_MAX_TTL_DAYS || 365) || 365;
const maxMs = maxDays * 24 * 3600 * 1000;
let ttl = requestedTtl || defaultTtl;
let clampMessage = '';

if (!ttl.forever && ttl.ms > maxMs) {
  ttl = { forever: false, ms: maxMs, label: `${maxDays} ngày` };
  clampMessage = `TTL vượt giới hạn nên Mia đã giảm còn ${maxDays} ngày.`;
}

const expiresAt = ttl.forever ? null : new Date(Date.now() + ttl.ms);
const expiresAtIso = expiresAt ? expiresAt.toISOString() : null;
const expiresAtSql = expiresAtIso ? `'${escapeSql(expiresAtIso)}'::timestamptz` : 'NULL';
const expiresAtDisplay = expiresAt ? expiresAt.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false }) : 'vĩnh viễn';
const publicBaseUrl = String($env.SHORTLINK_PUBLIC_BASE_URL || 'https://go.huynhminh.com').replace(/\\/+$/, '');
const digest = hashHex(`${parsedUrl.href}|${publicBaseUrl}`);
const candidateId8 = digest.slice(0, 8);
const candidateId10 = digest.slice(0, 10);
const candidateId12 = digest.slice(0, 12);
const lookupSql = `SELECT id, long_url, short_url, host, clicks, created_at, expires_at, updated_at, last_clicked_at FROM short_links WHERE long_url = '${escapeSql(parsedUrl.href)}' OR id IN ('${candidateId8}', '${candidateId10}', '${candidateId12}') ORDER BY created_at DESC;`;

return [{
  json: {
    chatId,
    deliveryMode,
    ok: true,
    longUrl: parsedUrl.href,
    host: parsedUrl.host,
    publicBaseUrl,
    expiresAtIso,
    expiresAtSql,
    expiresAtDisplay,
    requestedTtlLabel: requestedTtl ? requestedTtl.label : defaultTtl.label,
    effectiveTtlLabel: ttl.forever ? 'vĩnh viễn' : ttl.label,
    clampMessage,
    candidateId8,
    candidateId10,
    candidateId12,
    lookupSql
  }
}];"""

SHORTLINK_SUCCESS_CODE = """const source = $('Decide Final Record').item.json || $('Prepare Shortlink Request').item.json || {};
const row = $input.item.json || {};

const shortUrl = row.short_url || source.shortUrl || '';
const longUrl = row.long_url || source.longUrl || '';
const expiresAt = row.expires_at ? new Date(row.expires_at) : null;
const expiresAtDisplay = expiresAt
  ? expiresAt.toLocaleString('vi-VN', { timeZone: 'Asia/Ho_Chi_Minh', hour12: false })
  : source.expiresAtDisplay || 'vĩnh viễn';

let text = 'Đã tạo link ngắn.';
text += `\\nShort URL: ${shortUrl}`;
text += `\\nHết hạn: ${expiresAtDisplay}`;
text += `\\nLink gốc: ${longUrl}`;
if (source.clampMessage) text += `\\nLưu ý: ${source.clampMessage}`;

return [{ json: { chatId: source.chatId || '', text } }];"""

SHORTLINK_ERROR_CODE = """const source = $input.item.json || $('Prepare Shortlink Request').item.json || {};
return [{ json: { chatId: source.chatId || '', text: String(source.responseText || 'Không thể xử lý short link.') } }];"""

SHORTLINK_DECIDE_CODE = """const source = $('Prepare Shortlink Request').item.json || {};
const rows = $input.all().map((item) => item.json || {}).filter((row) => row.id || row.long_url);

function escapeSql(value = '') {
  return String(value || '').replace(/'/g, "''");
}

function isExpired(row) {
  return Boolean(row.expires_at && new Date(row.expires_at).getTime() <= Date.now());
}

const sameUrl = rows.find((row) => row.long_url === source.longUrl);
const byId = new Map(rows.filter((row) => row.id).map((row) => [row.id, row]));
const candidates = [source.candidateId8, source.candidateId10, source.candidateId12];
let selectedId = '';
let persistSql = '';
let shortUrl = '';

if (sameUrl) {
  selectedId = sameUrl.id;
  shortUrl = sameUrl.short_url || `${source.publicBaseUrl}/${selectedId}`;
  if (isExpired(sameUrl)) {
    persistSql = `UPDATE short_links SET expires_at = ${source.expiresAtSql}, updated_at = now() WHERE id = '${escapeSql(selectedId)}' RETURNING id, long_url, short_url, host, clicks, created_at, expires_at, updated_at, last_clicked_at;`;
  } else {
    persistSql = `SELECT id, long_url, short_url, host, clicks, created_at, expires_at, updated_at, last_clicked_at FROM short_links WHERE id = '${escapeSql(selectedId)}' LIMIT 1;`;
  }
} else {
  const freeCandidate = candidates.find((id) => !byId.has(id));
  if (!freeCandidate) {
    return [{ json: { chatId: source.chatId || '', ok: false, responseText: 'Không tạo được short link vì tất cả candidate ID đều bị trùng. Bạn thử lại sau nhé.' } }];
  }
  selectedId = freeCandidate;
  shortUrl = `${source.publicBaseUrl}/${selectedId}`;
  persistSql = `INSERT INTO short_links (id, long_url, short_url, host, expires_at, created_at, updated_at) VALUES ('${selectedId}', '${escapeSql(source.longUrl)}', '${escapeSql(shortUrl)}', '${escapeSql(source.host)}', ${source.expiresAtSql}, now(), now()) RETURNING id, long_url, short_url, host, clicks, created_at, expires_at, updated_at, last_clicked_at;`;
}

return [{
  json: {
    ...source,
    ok: true,
    id: selectedId,
    shortUrl,
    persistSql
  }
}];"""


def update_node(workflow: dict, node_name: str, parameters: dict) -> None:
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            node["parameters"] = parameters
            return
    raise KeyError(f"Node {node_name!r} not found")


def find_node(workflow: dict, node_name: str) -> dict | None:
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            return node
    return None


def ensure_normalize_tool_node(workflow: dict) -> None:
    if not any(node["name"] == "Chuẩn Hóa Tool Text" for node in workflow["nodes"]):
        workflow["nodes"].append(
            {
                "parameters": {"jsCode": NORMALIZE_TOOL_TEXT_CODE},
                "id": f"normalize-tool-text-{workflow.get('name', 'wf')}",
                "name": "Chuẩn Hóa Tool Text",
                "type": "n8n-nodes-base.code",
                "typeVersion": 2,
                "position": [560, 160],
            }
        )
    else:
        update_node(workflow, "Chuẩn Hóa Tool Text", {"jsCode": NORMALIZE_TOOL_TEXT_CODE})


def remove_node_if_exists(workflow: dict, node_name: str) -> None:
    workflow["nodes"] = [node for node in workflow["nodes"] if node["name"] != node_name]
    workflow["connections"].pop(node_name, None)
    for connection in workflow["connections"].values():
        main = connection.get("main", [])
        for output_group in main:
            output_group[:] = [target for target in output_group if target.get("node") != node_name]


def reroute_into_normalizer(workflow: dict) -> None:
    for connection in workflow["connections"].values():
        main = connection.get("main", [])
        for output_group in main:
            for target in output_group:
                if target["node"] == "Có ChatId?":
                    target["node"] = "Chuẩn Hóa Tool Text"

    workflow["connections"]["Chuẩn Hóa Tool Text"] = {
        "main": [[{"node": "Có ChatId?", "type": "main", "index": 0}]]
    }


def cleanup_telegram_node(workflow: dict) -> None:
    node = find_node(workflow, "Gửi Telegram Trực Tiếp")
    if not node:
        return
    params = node.get("parameters", {})
    body_params = params.get("bodyParameters", {}).get("parameters", [])
    filtered: list[dict] = []
    for item in body_params:
        if item.get("name") == "parse_mode":
            continue
        if item.get("name") == "text":
            item["value"] = "={{ $json.text }}"
        filtered.append(item)
    params.setdefault("bodyParameters", {})["parameters"] = filtered
    node["parameters"] = params


def main() -> None:
    for path in WORKFLOWS:
        workflow = json.loads(path.read_text())
        ensure_normalize_tool_node(workflow)
        remove_node_if_exists(workflow, "Backup HTML Text")
        reroute_into_normalizer(workflow)
        update_node(workflow, "Có ChatId?", BOOL_CHAT_CONDITION)
        workflow["connections"]["Có ChatId?"] = {
            "main": [
                [{"node": "Giữ Text Khi Thiếu ChatId", "type": "main", "index": 0}],
                [{"node": "Gửi Telegram Trực Tiếp", "type": "main", "index": 0}],
            ]
        }
        cleanup_telegram_node(workflow)

        if path.name == "workflow_sub_weather.json":
            update_node(workflow, "Chuẩn Bị Địa Điểm", {"jsCode": WEATHER_PREP_CODE})
            update_node(workflow, "Tổng Hợp Thời Tiết", {"jsCode": WEATHER_FORMAT_CODE})

        if path.name == "workflow_sub_search.json":
            update_node(workflow, "Chuẩn Bị Query", {"jsCode": SEARCH_PREP_CODE})
            update_node(workflow, "Tổng Hợp Kết Quả", {"jsCode": SEARCH_FORMAT_CODE})

        if path.name == "workflow_sub_news.json":
            update_node(workflow, "Chuẩn bị URL News", {"jsCode": NEWS_CODE})
            update_node(workflow, "Format Tin Tức", {"jsCode": NEWS_FORMAT_CODE})

        if path.name == "workflow_sub_gold.json":
            update_node(workflow, "Chuẩn bị ChatID", {"jsCode": GOLD_CHAT_CODE})
            update_node(workflow, "Tổng Hợp Giá Vàng", {"jsCode": GOLD_FORMAT_CODE})

        if path.name == "workflow_shortlink_create.json":
            update_node(workflow, "Prepare Shortlink Request", {"jsCode": SHORTLINK_PREP_CODE})
            update_node(workflow, "Decide Final Record", {"jsCode": SHORTLINK_DECIDE_CODE})
            update_node(workflow, "Format Success Response", {"jsCode": SHORTLINK_SUCCESS_CODE})
            update_node(workflow, "Format Error Response", {"jsCode": SHORTLINK_ERROR_CODE})

        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {path}")


if __name__ == "__main__":
    main()
