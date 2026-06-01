# Google Gmail Domain

## Kiến trúc hiện tại

Mia ưu tiên gọi Gmail theo action-level capability thay vì đi qua `Gmail Master` để đoán lại ý người dùng.

Action hiện có:

- `gmail.help`
- `gmail.list_inbox`
- `gmail.read_email`
- `gmail.search_email`
- `gmail.send_email`
- `gmail.draft_email`
- `gmail.reply_email`

## File trong domain

- `workflow_sub_google_gmail_help.json`
- `workflow_sub_google_gmail_list_inbox.json`
- `workflow_sub_google_gmail_read_email.json`
- `workflow_sub_google_gmail_search_email.json`
- `workflow_sub_google_gmail_send_email.json`
- `workflow_sub_google_gmail_draft_email.json`
- `workflow_sub_google_gmail_reply_email.json`
- `workflow_sub_google_gmail_master.json`

## Vai trò của `master`

`workflow_sub_google_gmail_master.json` là lớp tương thích cũ:

- vẫn hữu ích nếu có workflow khác còn bắn câu text tự nhiên vào Gmail domain
- không còn là đường chạy ưu tiên của Mia core

## Lệnh mẫu

- `xem mail`
- `đọc mail hóa đơn mới nhất`
- `tìm mail openrouter`
- `gửi mail cho a@b.com tiêu đề ...`
- `soạn mail cho team nội dung ...`
- `trả lời mail từ cô giáo rằng ...`

## Ghi chú

- `gmail.list_inbox` và `gmail.search_email` hiện đã giữ được link email khi Mia trả lời.
- Các action có side effect mạnh như gửi/trả lời mail nên test cẩn thận bằng tài khoản thật.
