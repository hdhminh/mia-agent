# Domain Architecture

## Đường chạy chính của Mia

```text
Telegram
-> Mia: Main Gateway (n8n)
-> mia-core (FastAPI + LangChain)
-> domain tools
-> Mia: Tool Gateway (n8n)
-> action-level workflows / services
-> mia-core tổng hợp câu trả lời
-> Telegram
```

## Domain chính

### `memory`

- Python repository chính: `langchain_core/mia_core/memory.py`
- Workflow phụ trợ:
  - `Memory: Search RAG`
  - `Memory: Write RAG`
  - `Memory: Recent`

### `shortlink`

- Workflow chính:
  - `workflow_shortlink_create`
  - `workflow_shortlink_redirect`

### `google/calendar`

- action-level workflows:
  - `calendar.help`
  - `calendar.list_today`
  - `calendar.list_tomorrow`
  - `calendar.find_event`
  - `calendar.create_event`
  - `calendar.delete_event`
  - `calendar.check_availability`

### `google/gmail`

- action-level workflows:
  - `gmail.help`
  - `gmail.list_inbox`
  - `gmail.read_email`
  - `gmail.search_email`
  - `gmail.send_email`
  - `gmail.draft_email`
  - `gmail.reply_email`

### `google/drive`

- action-level workflows:
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

### `google/docs`

- action-level workflows:
  - `docs.help`
  - `docs.search_doc`
  - `docs.read_doc`
  - `docs.create_doc`
  - `docs.append_doc`
  - `docs.delete_doc`

### `google/sheets`

- action-level workflows:
  - `sheets.help`
  - `sheets.search_sheet`
  - `sheets.read_sheet`
  - `sheets.create_sheet`
  - `sheets.append_row`
  - `sheets.update_cell`
  - `sheets.delete_sheet`

### Mini-domains khác

- `weather`
- `gold`
- `news`
- `search`

## Compatibility layer

Các file `*_master.json` trong `google/*` vẫn còn trong repo để:

- giữ tương thích với workflow cũ
- cho phép n8n flow khác gọi bằng text tự nhiên

Nhưng với Mia, đường ưu tiên hiện tại là:

- `mia_core.tools` gọi theo action-level tool
- `Mia: Tool Gateway` route thẳng vào leaf workflow phù hợp
