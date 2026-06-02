# Mia Capability Map

## Route Classes

- `chat_only`
  - model trả lời trực tiếp, không cần tool
- `direct_deterministic`
  - đi thẳng vào capability cụ thể, không vào full agent loop
- `agentic_domain`
  - dùng agent với toolset domain phù hợp
- `agentic_multistep`
  - dùng agent orchestration cho yêu cầu nhiều bước hoặc mơ hồ

## Direct Deterministic

- `memory_recent`
- `weather_get`
- `gold_get_price`
- `news_get`
- `search_web`
- `shortlink_create`
- `calendar_help`
- `calendar_list_today`
- `calendar_list_tomorrow`
- `gmail_help`
- `gmail_list_inbox`
- `drive_help`
- `drive_list_files`
- `drive_search_file`
- `docs_help`
- `docs_search_doc`
- `sheets_help`
- `sheets_search_sheet`

## Domain Agent Candidates

### `calendar`

- `calendar_find_event`
- `calendar_create_event`
- `calendar_delete_event`
- `calendar_check_availability`

### `gmail`

- `gmail_read_email`
- `gmail_search_email`
- `gmail_send_email`
- `gmail_draft_email`
- `gmail_reply_email`

### `workspace`

- `drive_get_file_info`
- `drive_create_folder`
- `drive_create_file`
- `drive_upload_file`
- `drive_download_file`
- `drive_share_file`
- `drive_move_file`
- `drive_rename_file`
- `drive_copy_file`
- `drive_delete_file`
- `drive_delete_folder`
- `drive_export_file`
- `docs_read_doc`
- `docs_create_doc`
- `docs_append_doc`
- `docs_delete_doc`
- `sheets_read_sheet`
- `sheets_create_sheet`
- `sheets_append_row`
- `sheets_update_cell`
- `sheets_delete_sheet`

## Current Direction

- Câu rõ ràng + ít side effect phải đi `direct_deterministic`.
- Câu nhiều bước nhưng bản chất chỉ cần `simple capability + style follow-up` vẫn ưu tiên direct path.
- Chỉ các thao tác domain sâu hoặc nhiều side effect mới vào `agentic_domain` / `agentic_multistep`.
