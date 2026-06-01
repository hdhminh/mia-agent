#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/home/huynhminh/Projects/n8n/google")


PATCHES = {
    ROOT / "gmail/workflow_sub_google_gmail_help.json": {
        "Huong Dan Gmail": """const source = $('Execute Workflow Trigger').item.json || {};
const msg = source.message || source.body?.message || source.payload?.message || {};
const chatId = source.chatId || msg.chat?.id || source.payload?.chatId || source.body?.chatId || '';

const text = [
  'Google Gmail',
  '',
  'Mia hỗ trợ các tác vụ:',
  '1. Xem hộp thư: xem mail, inbox, mail mới',
  '2. Đọc email: đọc mail từ Google, nội dung mail khách hàng',
  '3. Tìm kiếm email: tìm mail hợp đồng, search mail invoice',
  '4. Soạn nháp email: soạn mail cho test@gmail.com tiêu đề Chào bạn nội dung Hẹn gặp bạn ngày mai',
  '5. Gửi email: gửi mail test@gmail.com Chào bạn Nội dung thư',
  '6. Trả lời email: trả lời mail từ Google nội dung Cảm ơn bạn',
  '',
  'Lệnh nhanh:',
  '- gmail help',
  '- xem mail',
  '- đọc mail từ Google',
  '- tìm mail hóa đơn',
  '- soạn mail cho test@gmail.com',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "drive/workflow_sub_google_drive_help.json": {
        "Huong Dan Drive": """const source = $('Execute Workflow Trigger').item.json || {};
const msg = source.message || source.body?.message || source.payload?.message || {};
const chatId = source.chatId || msg.chat?.id || source.payload?.chatId || source.body?.chatId || '';

const text = [
  'Google Drive',
  '',
  'Mia hỗ trợ:',
  '- xem file gần đây',
  '- tìm file hoặc thư mục',
  '- xem thông tin file',
  '- tạo folder',
  '- tạo file text/code/data',
  '- upload hoặc tải file',
  '- copy, đổi tên, di chuyển file',
  '- chia sẻ file',
  '- xuất file Google Docs/Sheets/Slides',
  '- xóa file hoặc folder',
  '',
  'Ví dụ nhanh:',
  '- drive help',
  '- xem file drive',
  '- tìm file hợp đồng',
  '- thông tin file note.md',
  '- tạo folder Khách hàng',
  '- tạo file ghi-chu.txt nội dung Xin chào',
  '- tải file báo cáo.pdf',
  '- xuất file tài liệu sang pdf',
  '- đổi tên file old.txt thành new.txt',
  '- di chuyển file A vào folder B',
  '- xóa folder Dự án cũ',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "docs/workflow_sub_google_docs_help.json": {
        "Huong Dan Docs": """const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';

const text = [
  'Google Docs',
  '',
  'Mia hỗ trợ các tác vụ:',
  '- tạo doc',
  '- đọc nội dung doc',
  '- thêm nội dung vào doc',
  '- tìm doc',
  '- xóa doc',
  '',
  'Ví dụ nhanh:',
  '- docs help',
  '- tạo doc Project Plan nội dung Mục tiêu dự án',
  '- đọc doc Project Plan',
  '- thêm vào doc Project Plan: hôm nay đã sửa Drive Upload',
  '- tìm doc Project Plan',
  '- xóa doc Project Plan',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "docs/workflow_sub_google_docs_create_doc.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const created = $('Docs Create File').item.json || {};
const title = created.name || source.title || 'Không rõ tên';
const docId = created.id || '';
const link = created.webViewLink || (docId ? `https://docs.google.com/document/d/${docId}/edit` : '');
const contentLength = String(source.content || '').length;

let text = `Đã tạo Google Doc: ${title}`;
if (docId) text += `\\nID: ${docId}`;
if (contentLength) text += `\\nNội dung ban đầu: ${contentLength} ký tự`;
if (link) text += `\\nMở tài liệu: ${link}`;

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "docs/workflow_sub_google_docs_append_doc.json": {
        "Format Action": """const source = $('Build Append Request').item.json || $('Prepare Action').item.json || {};
const docId = source.docId || '';
const link = source.webViewLink || (docId ? `https://docs.google.com/document/d/${docId}/edit` : '');
const charCount = String(source.content || '').length;
const docName = source.docName || 'Không rõ tên';

let text = `Đã thêm nội dung vào Google Doc: ${docName}`;
if (docId) text += `\\nID: ${docId}`;
text += `\\nSố ký tự đã thêm: ${charCount}`;
if (link) text += `\\nMở tài liệu: ${link}`;

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "docs/workflow_sub_google_docs_delete_doc.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const item = $input.item.json || {};
const docId = item.id || source.docId || '';
const docName = item.name || source.docName || 'Không rõ tên';
const link = item.webViewLink || source.webViewLink || (docId ? `https://docs.google.com/document/d/${docId}/edit` : '');

let text = `Đã đưa Google Doc vào thùng rác: ${docName}`;
if (docId) text += `\\nID: ${docId}`;
if (link) text += `\\nMở tài liệu: ${link}`;

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "docs/workflow_sub_google_docs_read_doc.json": {
        "Format Action": """function collectText(node, out = []) {
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
const content = collectText(doc.body?.content || []).join('').replace(/\\n{3,}/g, '\\n\\n').trim();
let preview = content.slice(0, 3000) || '(Tài liệu rỗng)';

let text = `Nội dung Google Doc: ${title}`;
if (docId) text += `\\nID: ${docId}`;
if (link) text += `\\nMở tài liệu: ${link}`;
text += `\\n\\nXem trước:\\n${preview}`;
if (content.length > 3000) text += '\\n\\nNội dung đã được rút gọn.';

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_help.json": {
        "Huong Dan Sheets": """const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';

const text = [
  'Google Sheets',
  '',
  'Mia hỗ trợ các tác vụ:',
  '- tạo sheet',
  '- đọc dữ liệu sheet',
  '- thêm dòng',
  '- cập nhật ô',
  '- tìm sheet',
  '- xóa sheet',
  '',
  'Ví dụ nhanh:',
  '- sheets help',
  '- tạo sheet Chi tiêu',
  '- đọc sheet Chi tiêu',
  '- thêm dòng vào sheet Chi tiêu: cafe,30000,ăn uống',
  '- cập nhật sheet Chi tiêu ô B2 thành 35000',
  '- tìm sheet Chi tiêu',
  '- xóa sheet Chi tiêu',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_create_sheet.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const sheet = $input.item.json || {};
const spreadsheetId = sheet.spreadsheetId || '';
const title = sheet.properties?.title || source.title || 'Không rõ tên';
const link = spreadsheetId ? `https://docs.google.com/spreadsheets/d/${spreadsheetId}/edit` : '';

let text = `Đã tạo Google Sheet: ${title}`;
if (spreadsheetId) text += `\\nID: ${spreadsheetId}`;
if (link) text += `\\nMở bảng tính: ${link}`;

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_append_row.json": {
        "Format Action": """function getJson(nodeName) {
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
const sheetId = source.spreadsheetId || source.sheetId || '';
const link = source.webViewLink || (sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit` : '');
const updatedRange = result.updates?.updatedRange || result.updatedRange || '';
const shownTarget = source.sheetTab
  ? `${source.sheetName || 'Không rõ tên'} / tab ${source.sheetTab}`
  : (source.sheetName || 'Không rõ tên');
const addedColumns = Array.isArray(source.values) ? source.values.length : 0;

let text = `Đã thêm dòng vào Google Sheet: ${shownTarget}`;
if (sheetId) text += `\\nID: ${sheetId}`;
if (updatedRange) text += `\\nVùng cập nhật: ${updatedRange}`;
text += `\\nSố cột đã thêm: ${addedColumns}`;
if (link) text += `\\nMở bảng tính: ${link}`;

return [{ json: { chatId: source.chatId || result.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_delete_sheet.json": {
        "Format Action": """const source = $('Prepare Action').item.json || {};
const item = $input.item.json || {};
const sheetId = item.id || source.spreadsheetId || '';
const sheetName = item.name || source.sheetName || 'Không rõ tên';
const link = item.webViewLink || source.webViewLink || (sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit` : '');

let text = `Đã đưa Google Sheet vào thùng rác: ${sheetName}`;
if (sheetId) text += `\\nID: ${sheetId}`;
if (link) text += `\\nMở bảng tính: ${link}`;

return [{ json: { chatId: source.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_read_sheet.json": {
        "Format Action": """function getJson(nodeName) {
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
const limited = rows.slice(0, 30);
let preview = limited.map((row, index) => `${index + 1}. ${row.map((cell) => String(cell)).join(' | ')}`).join('\\n');
let truncated = rows.length > 30;
if (preview.length > 3000) {
  preview = preview.slice(0, 3000);
  truncated = true;
}

const sheetId = source.spreadsheetId || source.sheetId || '';
const link = source.webViewLink || (sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit` : '');
const shownRange = source.sheetTab ? `'${source.sheetTab}'!${source.range || 'A1:Z30'}` : (source.range || 'A1:Z30');

let text = `Nội dung Google Sheet: ${source.sheetName || source.name || 'Không rõ tên'}`;
if (sheetId) text += `\\nID: ${sheetId}`;
text += `\\nRange: ${shownRange}`;
if (link) text += `\\nMở bảng tính: ${link}`;
text += `\\n\\nDữ liệu xem trước:\\n${preview || '(Không có dữ liệu)'}`;
if (truncated) text += '\\n\\nNội dung đã được rút gọn.';

return [{ json: { chatId: source.chatId || result.chatId || '', text: text.trim() } }];""",
    },
    ROOT / "sheets/workflow_sub_google_sheets_update_cell.json": {
        "Format Action": """function getJson(nodeName) {
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
const sheetId = source.spreadsheetId || source.sheetId || '';
const link = source.webViewLink || (sheetId ? `https://docs.google.com/spreadsheets/d/${sheetId}/edit` : '');
const updatedRange = result.updatedRange || result.updatedData?.range || '';
const shownCell = source.sheetTab ? `'${source.sheetTab}'!${source.cell || ''}` : (source.cell || '');
const shownTarget = source.sheetTab
  ? `${source.sheetName || 'Không rõ tên'} / tab ${source.sheetTab}`
  : (source.sheetName || 'Không rõ tên');

let text = `Đã cập nhật ô trong Google Sheet: ${shownTarget}`;
if (sheetId) text += `\\nID: ${sheetId}`;
text += `\\nÔ đã cập nhật: ${updatedRange || shownCell}`;
text += `\\nGiá trị mới: ${source.value || ''}`;
if (link) text += `\\nMở bảng tính: ${link}`;

return [{ json: { chatId: source.chatId || result.chatId || '', text: text.trim() } }];""",
    },
}


def update_node(workflow: dict, node_name: str, js_code: str) -> None:
    for node in workflow["nodes"]:
        if node["name"] == node_name:
            node["parameters"]["jsCode"] = js_code
            return
    raise KeyError(f"{node_name!r} not found in {workflow.get('name')}")


def main() -> None:
    for path, node_map in PATCHES.items():
        workflow = json.loads(path.read_text())
        for node_name, js_code in node_map.items():
            update_node(workflow, node_name, js_code)
        path.write_text(json.dumps(workflow, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {path}")


if __name__ == "__main__":
    main()
