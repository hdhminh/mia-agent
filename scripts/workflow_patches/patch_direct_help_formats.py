#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


PATCHES = {
    ROOT / "google/calendar/workflow_sub_google_calendar_help.json": {
        "Huong Dan Calendar": """const source = $('Execute Workflow Trigger').item.json || {};

const msg =
  source.message ||
  source.body?.message ||
  source.payload?.message ||
  {};

const chatId =
  source.chatId ||
  msg.chat?.id ||
  source.payload?.chatId ||
  source.body?.chatId ||
  '';

const text = [
  'Mia có thể hỗ trợ Google Calendar cho anh Minh ở các việc như xem lịch, tìm sự kiện, tạo lịch, huỷ lịch và kiểm tra giờ rảnh.',
  '',
  'Anh Minh thử vài câu kiểu này là được:',
  '- lịch hôm nay',
  '- lịch ngày mai',
  '- tìm lịch họp khách',
  '- tạo lịch họp team lúc 15h mai',
  '- huỷ lịch phỏng vấn ngày mai',
  '- kiểm tra lịch rảnh 9h-10h mai',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "google/gmail/workflow_sub_google_gmail_help.json": {
        "Huong Dan Gmail": """const source = $('Execute Workflow Trigger').item.json || {};
const msg = source.message || source.body?.message || source.payload?.message || {};
const chatId = source.chatId || msg.chat?.id || source.payload?.chatId || source.body?.chatId || '';

const text = [
  'Mia có thể hỗ trợ Gmail cho anh Minh theo vài việc chính như xem hộp thư, đọc mail, tìm mail, soạn nháp, gửi mail và trả lời mail.',
  '',
  'Anh Minh có thể thử ngay mấy câu như:',
  '- xem mail',
  '- đọc mail từ Google',
  '- tìm mail hóa đơn',
  '- soạn mail cho test@gmail.com tiêu đề Chào bạn nội dung Hẹn gặp bạn ngày mai',
  '- gửi mail test@gmail.com tiêu đề Chào bạn nội dung Đây là mail thử',
  '- trả lời mail từ Google nội dung Cảm ơn bạn',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "google/drive/workflow_sub_google_drive_help.json": {
        "Huong Dan Drive": """const source = $('Execute Workflow Trigger').item.json || {};
const msg = source.message || source.body?.message || source.payload?.message || {};
const chatId = source.chatId || msg.chat?.id || source.payload?.chatId || source.body?.chatId || '';

const text = [
  'Google Drive hiện cho phép Mia hỗ trợ anh Minh ở các việc như xem file gần đây, tìm file hoặc thư mục, xem thông tin file, tạo folder, tạo file, chia sẻ, đổi tên, di chuyển và xoá file.',
  '',
  'Anh Minh có thể bắt đầu bằng mấy câu như:',
  '- xem file drive',
  '- tìm file hợp đồng',
  '- thông tin file note.md',
  '- tạo folder Khách hàng',
  '- tạo file ghi-chu.txt nội dung Xin chào',
  '- đổi tên file old.txt thành new.txt',
  '- di chuyển file A vào folder B',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "google/docs/workflow_sub_google_docs_help.json": {
        "Huong Dan Docs": """const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';

const text = [
  'Với Google Docs, Mia có thể giúp anh Minh tạo tài liệu, đọc nội dung, thêm nội dung, tìm tài liệu và xoá tài liệu khi cần.',
  '',
  'Ví dụ dễ dùng nhất là:',
  '- tạo doc Project Plan nội dung Mục tiêu dự án',
  '- đọc doc Project Plan',
  '- thêm vào doc Project Plan: hôm nay đã sửa Drive Upload',
  '- tìm doc Project Plan',
  '- xóa doc Project Plan',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
    ROOT / "google/sheets/workflow_sub_google_sheets_help.json": {
        "Huong Dan Sheets": """const source = $('Execute Workflow Trigger').item.json || {};
const payload = source.payload || {};
const message = source.message || payload.message || payload.body?.message || {};
const chatId = source.chatId || message.chat?.id || payload.chatId || '';

const text = [
  'Với Google Sheets, Mia có thể tạo bảng tính, đọc dữ liệu, thêm dòng, cập nhật ô, tìm sheet và xoá sheet.',
  '',
  'Anh Minh thử nhanh như sau:',
  '- tạo sheet Chi tiêu',
  '- đọc sheet Chi tiêu',
  '- thêm dòng vào sheet Chi tiêu: cafe,30000,ăn uống',
  '- cập nhật sheet Chi tiêu ô B2 thành 35000',
  '- tìm sheet Chi tiêu',
  '- xóa sheet Chi tiêu',
].join('\\n');

return [{ json: { chatId, text } }];""",
    },
}


def main() -> None:
    for path, node_map in PATCHES.items():
        data = json.loads(path.read_text())
        for node in data.get("nodes", []):
            code = node_map.get(node.get("name"))
            if code is None:
                continue
            node.setdefault("parameters", {})["jsCode"] = code
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        print(f"patched {path}")


if __name__ == "__main__":
    main()
