#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def save_workflow(path: Path, workflow: dict) -> None:
    path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")


def patch_gateway_prepare() -> None:
    path = ROOT / "workflows/core/workflow_mia_tool_gateway.json"
    workflow = json.loads(path.read_text())
    for node in workflow["nodes"]:
        if node["name"] != "Prepare Tool Request":
            continue
        code = node["parameters"]["jsCode"]
        old = """  'drive.upload_file': {\n    workflowKey: 'drive.upload_file',\n    build: (a) => ({ text: clean(a.instruction) || 'upload file' }),\n  },"""
        new = """  'drive.upload_file': {\n    workflowKey: 'drive.upload_file',\n    build: (a) => ({\n      text: clean(a.instruction) || (clean(a.fileName) ? `upload file ${clean(a.fileName)}` : 'upload file'),\n      fileId: clean(a.fileId || a.telegramFileId),\n      telegramFileId: clean(a.telegramFileId || a.fileId),\n      fileName: clean(a.fileName),\n      mimeType: clean(a.mimeType),\n      folderId: clean(a.folderId),\n      attachmentKind: clean(a.attachmentKind),\n      hasAttachment: Boolean(a.hasAttachment),\n    }),\n  },"""
        if new in code:
            print("workflow_mia_tool_gateway.json:Prepare Tool Request already patched")
            return
        if old not in code:
            raise ValueError("Could not find drive.upload_file block in Prepare Tool Request")
        node["parameters"]["jsCode"] = code.replace(old, new, 1)
        save_workflow(path, workflow)
        print("patched workflow_mia_tool_gateway.json:Prepare Tool Request")
        return
    raise ValueError("Prepare Tool Request node not found")


def patch_drive_upload_workflow() -> None:
    path = ROOT / "google/drive/workflow_sub_google_drive_upload_file.json"
    workflow = json.loads(path.read_text())
    nodes = workflow["nodes"]
    by_name = {node["name"]: node for node in nodes}

    by_name["Prepare Action"]["parameters"]["jsCode"] = """const source = $('Execute Workflow Trigger').item.json || {};
const args = source.args || source.payload?.args || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || payload.payload?.message || {};

const chatId = source.chatId || message.chat?.id || payload.chatId || payload.payload?.chatId || '';
const raw = String(source.rawText || source.text || args.instruction || message.text || message.caption || payload.text || payload.rawText || '').trim();

const document = source.document || message.document || payload.document || payload.payload?.document || payload.payload?.message?.document || null;
const video = source.video || message.video || payload.video || payload.payload?.video || payload.payload?.message?.video || null;
const audio = source.audio || message.audio || message.voice || payload.audio || payload.payload?.audio || payload.payload?.message?.audio || payload.payload?.message?.voice || null;
const photo = source.photo || message.photo || payload.photo || payload.payload?.photo || payload.payload?.message?.photo || null;

const photoItem = Array.isArray(photo) && photo.length ? photo[photo.length - 1] : photo;

const explicitFileId = String(
  source.telegramFileId ||
  source.fileId ||
  args.telegramFileId ||
  args.fileId ||
  payload.telegramFileId ||
  payload.fileId ||
  ''
).trim();
const telegramFileId = explicitFileId || document?.file_id || video?.file_id || audio?.file_id || photoItem?.file_id || '';
const fileName =
  String(source.fileName || args.fileName || payload.fileName || '').trim() ||
  document?.file_name ||
  video?.file_name ||
  audio?.file_name ||
  (photoItem?.file_id ? `telegram-photo-${photoItem.file_id}.jpg` : 'upload.bin');
const mimeType =
  String(source.mimeType || args.mimeType || payload.mimeType || '').trim() ||
  document?.mime_type ||
  video?.mime_type ||
  audio?.mime_type ||
  (photoItem?.file_id ? 'image/jpeg' : 'application/octet-stream');
const folderId = String(source.folderId || args.folderId || payload.folderId || 'root').trim() || 'root';
const binaryPropertyName = 'data';

const hasTarget = Boolean(telegramFileId);
const guidance = hasTarget
  ? ''
  : 'Bạn hãy gửi kèm file hoặc ảnh rồi nhập caption như "upload file này vào drive" để Mia lưu giúp bạn.';

return [{
  json: {
    ...source,
    args,
    payload,
    message,
    chatId,
    raw,
    rawText: raw,
    telegramFileId,
    fileId: telegramFileId,
    fileName,
    mimeType,
    folderId,
    binaryPropertyName,
    hasTarget,
    response: guidance,
    text: guidance,
  }
}];"""

    if "Resolve Telegram File" not in by_name:
        nodes.append(
            {
                "parameters": {
                    "method": "GET",
                    "url": '={{ `https://api.telegram.org/bot${$env.TELEGRAM_BOT_TOKEN}/getFile?file_id=${encodeURIComponent($json.telegramFileId)}` }}',
                    "options": {},
                },
                "id": "ac83c4fa-9e81-4f92-9c74-telegram-get-file",
                "name": "Resolve Telegram File",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "continueOnFail": True,
                "position": [0, 0],
            }
        )
        by_name = {node["name"]: node for node in nodes}
    else:
        by_name["Resolve Telegram File"]["continueOnFail"] = True

    if "Co URL Download?" not in by_name:
        nodes.append(
            {
                "parameters": {
                    "conditions": {"boolean": [{"value1": "={{ Boolean($json.telegramDownloadUrl) }}", "value2": True}]}
                },
                "id": "c9eb1c6a-11d2-4f0f-9c2f-drive-upload-has-url",
                "name": "Co URL Download?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 1,
                "position": [360, 0],
            }
        )
        by_name = {node["name"]: node for node in nodes}
    else:
        by_name["Co URL Download?"]["parameters"] = {
            "conditions": {"boolean": [{"value1": "={{ Boolean($json.telegramDownloadUrl) }}", "value2": True}]}
        }
        by_name["Co URL Download?"]["typeVersion"] = 1

    by_name["Build Telegram Download URL"]["parameters"]["jsCode"] = """const source = $('Prepare Action').item.json || {};
const result = $input.item.json?.result || {};
const filePath = String(result.file_path || '').trim();
if (!filePath) {
  const fallback = 'Không lấy được file_path từ Telegram getFile.';
  return [{ json: { ...source, response: fallback, text: fallback } }];
}
return [{
  json: {
    ...source,
    telegramFilePath: filePath,
    telegramDownloadUrl: `https://api.telegram.org/file/bot${$env.TELEGRAM_BOT_TOKEN}/${filePath}`
  }
}];"""

    by_name["Format Action"]["parameters"]["jsCode"] = """const source = $('Prepare Action').item.json || {};
const item = $input.item.json || {};

const fileName = String(item.name || source.fileName || 'Không rõ tên').trim();
const fileId = String(item.id || '').trim();
const mimeType = String(item.mimeType || source.mimeType || '').trim();
const link = String(item.webViewLink || item.webContentLink || (fileId ? `https://drive.google.com/file/d/${fileId}/view` : '')).trim();

if (!fileId) {
  const fallback = String(item.response || source.response || '').trim() || 'Mia chưa upload được file lên Google Drive.';
  return [{
    json: {
      chatId: source.chatId || item.chatId || '',
      text: fallback,
      links: [],
      result: {},
      meta: { folderId: String(source.folderId || '').trim() }
    }
  }];
}

let text = `Mia đã upload file "${fileName}" lên Google Drive`;
if (link) {
  text += `.\\nMở file: ${link}`;
} else {
  text += '.';
}

return [{
  json: {
    chatId: source.chatId || item.chatId || '',
    text,
    links: link ? [link] : [],
    result: {
      id: fileId,
      name: fileName,
      mimeType,
      webViewLink: link,
      folderId: String(source.folderId || '').trim()
    },
    meta: {
      fileId,
      mimeType,
      folderId: String(source.folderId || '').trim()
    }
  }
}];"""

    workflow["connections"]["Co File Telegram?"] = {
        "main": [
            [{"node": "Resolve Telegram File", "type": "main", "index": 0}],
            [{"node": "Format Action", "type": "main", "index": 0}],
        ]
    }
    workflow["connections"]["Resolve Telegram File"] = {
        "main": [[{"node": "Build Telegram Download URL", "type": "main", "index": 0}]]
    }
    workflow["connections"]["Build Telegram Download URL"] = {
        "main": [[{"node": "Co URL Download?", "type": "main", "index": 0}]]
    }
    workflow["connections"]["Co URL Download?"] = {
        "main": [
            [{"node": "Download Telegram Binary", "type": "main", "index": 0}],
            [{"node": "Format Action", "type": "main", "index": 0}],
        ]
    }

    save_workflow(path, workflow)
    print("patched workflow_sub_google_drive_upload_file.json")


def main() -> None:
    patch_gateway_prepare()
    patch_drive_upload_workflow()


if __name__ == "__main__":
    main()
