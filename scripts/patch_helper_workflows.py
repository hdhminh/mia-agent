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

NEWS_CODE = """const source = $input.item.json || {};
const msg = source.message || source.body?.message || {};
const directChatId = String(source.chatId || msg.chat?.id || '').trim();
const deliveryMode = String(source.deliveryMode || source.payload?.deliveryMode || '').trim().toLowerCase();
const scheduledFallbackChatId = String($env.TELEGRAM_ADMIN_CHAT_ID || '').trim();
const rawText = String(msg.text || source.text || source.rawText || source.query || '').trim();
const text = rawText.toLowerCase();

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
if (isAuto) {
  topics = ['kinh-doanh', 'the-gioi', 'so-hoa'];
} else {
  if (text.includes('kinhdoanh') || text.includes('business')) topics.push('kinh-doanh');
  if (text.includes('thegioi') || text.includes('world')) topics.push('the-gioi');
  if (text.includes('congnghe') || text.includes('tech') || text.includes('sohoa')) topics.push('so-hoa');
  if (text.includes('thoisu') || text.includes('news')) topics.push('thoi-su');
  if (text.includes('suckhoe') || text.includes('health')) topics.push('suc-khoe');
  if (text.includes('thethao') || text.includes('sport')) topics.push('the-thao');
  if (text.includes('giaitri') || text.includes('entertainment')) topics.push('giai-tri');
  if (text.includes('phapluat') || text.includes('law')) topics.push('phap-luat');
  if (text.includes('giaoduc') || text.includes('education')) topics.push('giao-duc');
  if (text.includes('doisong') || text.includes('life')) topics.push('doi-song');
  if (text.includes('xe') || text.includes('car')) topics.push('xe');
  if (text.includes('dulich') || text.includes('travel')) topics.push('du-lich');
  if (text.includes('khoahoc') || text.includes('science')) topics.push('khoa-hoc');

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

return [{
  json: {
    ...source,
    chatId,
    isAuto,
    text,
    rawText,
    topics,
    topicNames,
    feedMap
  }
}];"""


def update_node(workflow: dict, node_name: str, parameters: dict) -> None:
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            node["parameters"] = parameters
            return
    raise KeyError(f"Node {node_name!r} not found")


def main() -> None:
    for path in WORKFLOWS:
        workflow = json.loads(path.read_text())
        update_node(workflow, "Có ChatId?", BOOL_CHAT_CONDITION)
        workflow["connections"]["Có ChatId?"] = {
            "main": [
                [{"node": "Giữ Text Khi Thiếu ChatId", "type": "main", "index": 0}],
                [{"node": "Gửi Telegram Trực Tiếp", "type": "main", "index": 0}],
            ]
        }

        if path.name == "workflow_sub_gold.json":
            update_node(workflow, "Chuẩn bị ChatID", {"jsCode": GOLD_CHAT_CODE})

        if path.name == "workflow_sub_news.json":
            update_node(workflow, "Chuẩn bị URL News", {"jsCode": NEWS_CODE})

        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {path}")


if __name__ == "__main__":
    main()
