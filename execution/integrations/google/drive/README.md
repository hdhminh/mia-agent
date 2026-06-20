# Google Drive Domain

## Kiến trúc hiện tại

Drive là domain lớn nhất phía Google, và Mia hiện gọi trực tiếp theo action-level capability qua `Mia: Tool Gateway`.

Action chính:

- `drive.help`
- `drive.list_files`
- `drive.search_file`
- `drive.get_file_info`
- `drive.create_folder`
- `drive.create_file`
- `drive.upload_file`
- `drive.download_file`
- `drive.share_file`
- `drive.move_file`
- `drive.rename_file`
- `drive.copy_file`
- `drive.delete_file`
- `drive.delete_folder`
- `drive.export_file`

## File trong domain

- `workflow_sub_google_drive_list_files.json`
- `workflow_sub_google_drive_search_file.json`
- `workflow_sub_google_drive_get_file_info.json`
- `workflow_sub_google_drive_create_folder.json`
- `workflow_sub_google_drive_create_file.json`
- `workflow_sub_google_drive_upload_file.json`
- `workflow_sub_google_drive_download_file.json`
- `workflow_sub_google_drive_share_file.json`
- `workflow_sub_google_drive_move_file.json`
- `workflow_sub_google_drive_rename_file.json`
- `workflow_sub_google_drive_copy_file.json`
- `workflow_sub_google_drive_delete_file.json`
- `workflow_sub_google_drive_delete_folder.json`
- `workflow_sub_google_drive_export_file.json`
- `workflow_sub_google_drive_help.json`
- `workflow_sub_google_drive_master.json`

## Vai trò của `master`

`workflow_sub_google_drive_master.json` còn giữ lại cho compatibility:

- dùng khi workflow cũ còn gọi theo text tự nhiên
- không còn là đường chạy chính của Mia

## Lệnh mẫu

- `xem file drive`
- `tìm file project`
- `chi tiết file báo cáo`
- `tạo folder Khách hàng`
- `share file A cho email@example.com`
- `xóa file A`

## Ghi chú

- `drive.search_file` và `drive.list_files` hiện đã giữ được link trong câu trả lời cuối của Mia.
- `drive.upload_file` hiện ưu tiên structured args với `fileId/telegramFileId`, `fileName`, `mimeType`, `folderId` trước khi fallback về `instruction`.
- Các workflow local cho `delete_file` và `share_file` đã được thêm credential để tránh lệch với live instance.
