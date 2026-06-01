# Google Sheets Domain

## Kiến trúc hiện tại

Mia ưu tiên gọi Sheets theo action-level capability qua `Mia: Tool Gateway`.

Action chính:

- `sheets.help`
- `sheets.search_sheet`
- `sheets.read_sheet`
- `sheets.create_sheet`
- `sheets.append_row`
- `sheets.update_cell`
- `sheets.delete_sheet`

## File trong domain

- `workflow_sub_google_sheets_help.json`
- `workflow_sub_google_sheets_search_sheet.json`
- `workflow_sub_google_sheets_read_sheet.json`
- `workflow_sub_google_sheets_create_sheet.json`
- `workflow_sub_google_sheets_append_row.json`
- `workflow_sub_google_sheets_update_cell.json`
- `workflow_sub_google_sheets_delete_sheet.json`
- `workflow_sub_google_sheets_master.json`

## Vai trò của `master`

`workflow_sub_google_sheets_master.json` hiện là lớp tương thích:

- vẫn dùng được cho workflow cũ còn gửi text tự nhiên
- không còn là đường ưu tiên của Mia

## Lệnh mẫu

- `sheets help`
- `tìm sheet test`
- `xem sheet Chi tiêu`
- `tạo sheet Test Mia`
- `thêm dòng vào sheet Chi tiêu: cafe,30000,ăn uống`
- `cập nhật sheet Chi tiêu ô B2 thành 35000`
- `xóa sheet Test Mia`

## Ghi chú

- `sheets.search_sheet` hiện đã giữ được link bảng tính khi Mia trả lời.
- Nếu cần export CSV/XLSX/PDF thì vẫn nên đi qua Drive domain.
