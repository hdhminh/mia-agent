# Google Calendar Domain

## Kiến trúc hiện tại

Đường chính của Mia không còn phụ thuộc vào `Calendar Master` để parse text rồi lookup workflow ID động nữa.

Mia hiện gọi action-level workflow qua `Mia: Tool Gateway`, ví dụ:

- `calendar.help`
- `calendar.list_today`
- `calendar.list_tomorrow`
- `calendar.find_event`
- `calendar.create_event`
- `calendar.delete_event`
- `calendar.check_availability`

## File trong domain

- `workflow_sub_google_calendar_help.json`
- `workflow_sub_google_calendar_list_today.json`
- `workflow_sub_google_calendar_list_tomorrow.json`
- `workflow_sub_google_calendar_find_event.json`
- `workflow_sub_google_calendar_create_event.json`
- `workflow_sub_google_calendar_delete_event.json`
- `workflow_sub_google_calendar_check_availability.json`
- `workflow_sub_google_calendar_master.json`

## Vai trò của `master`

`workflow_sub_google_calendar_master.json` hiện chỉ nên xem là lớp tương thích cũ:

- hữu ích nếu workflow khác trong n8n vẫn còn gọi kiểu text tự nhiên
- không phải đường ưu tiên cho Mia nữa

## Lệnh mẫu

- `lịch hôm nay`
- `lịch ngày mai`
- `tìm lịch tuần sau`
- `tạo lịch họp team lúc 15h mai`
- `xóa lịch demo chiều mai`
- `kiểm tra lịch rảnh chiều thứ 4`

## Ghi chú

- Calendar leaf workflows trả `text` plain cho Mia đọc.
- Nếu cần giữ compatibility với Telegram direct-send thì vẫn có thể truyền `chatId`.
