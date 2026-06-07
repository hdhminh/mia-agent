#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "google/gmail/workflow_sub_google_gmail_reply_email.json"

PARSE_CODE = r"""
const source = $('Execute Workflow Trigger').item.json || {};
const args = source.args || source.payload?.args || {};
const payload = source.payload || {};
const message = source.message || payload.message || {};
const chatId = source.chatId || message.chat?.id || '';
const raw = String(source.rawText || source.text || message.text || '').trim();

let cleaned = raw.replace(/^(tra loi mail|trả lời mail|tra loi email|trả lời email|reply mail|reply email)\s*/i, '').trim();
const explicitSearchQuery = String(source.searchQuery || args.searchQuery || '').trim();
const directMessageId = String(source.messageId || args.messageId || '').trim();
const directReplyBody = String(source.body || args.body || '').trim();

const parts = cleaned.split('\n').map((line) => line.trim()).filter(Boolean);
let searchQuery = explicitSearchQuery;
let replyBody = directReplyBody;

if (!replyBody && parts.length >= 2) {
  searchQuery = searchQuery || parts[0];
  replyBody = parts.slice(1).join('\n');
} else if (!replyBody && parts.length === 1) {
  const spaceParts = parts[0].split(/\s{2,}|\t/);
  if (spaceParts.length >= 2) {
    searchQuery = searchQuery || spaceParts[0];
    replyBody = spaceParts.slice(1).join(' ');
  }
}

const hasBody = Boolean(replyBody);
const hasExactTarget = Boolean(directMessageId);
const isReady = hasExactTarget && hasBody;

let response = '';
if (!hasBody) {
  response = [
    'Mia cần nội dung trả lời trước khi gửi email.',
    '',
    'Cách an toàn:',
    '- đọc email cần trả lời trước',
    '- sau đó reply bằng messageId cụ thể'
  ].join('\n');
} else if (!hasExactTarget) {
  response = [
    'Mia chưa gửi reply vì chưa có messageId cụ thể.',
    '',
    searchQuery ? `Từ khóa bạn đưa: ${searchQuery}` : '',
    'Để tránh trả lời nhầm email, hãy tìm/đọc email trước rồi reply đúng messageId.'
  ].filter(Boolean).join('\n');
}

return [{
  json: {
    ...source,
    chatId,
    messageId: directMessageId,
    searchQuery,
    replyBody,
    isReady,
    response
  }
}];
"""


def main() -> None:
    workflow = json.loads(PATH.read_text(encoding="utf-8"))
    for node in workflow.get("nodes", []):
        if node.get("name") == "Parse Tra Loi Email":
            node.setdefault("parameters", {})["jsCode"] = PARSE_CODE.strip() + "\n"
            break
    else:
        raise RuntimeError("Parse Tra Loi Email not found")
    PATH.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("patched gmail reply safety")


if __name__ == "__main__":
    main()
