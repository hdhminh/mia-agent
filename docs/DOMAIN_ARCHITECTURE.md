# Domain Architecture

## Main Runtime Path

```text
Telegram
-> Mia: Main Gateway (n8n)
-> mia-core Router
   -> DirectExecutor
   -> Domain agent/toolset path
-> Mia: Tool Gateway (n8n)
-> action-level workflows / services
-> response normalizer
-> Telegram
```

## Core Domains

### `memory`

- Python repository: `langchain_core/mia_core/memory.py`
- Local capabilities:
  - `memory_search`
  - `memory_recent`
  - `memory_write`
- Workflow support:
  - `Memory: Search RAG`
  - `Memory: Write RAG`
  - `Memory: Recent`

### `weather`

- Capability:
  - `weather.get`
- Current path:
  - deterministic direct

### `gold`

- Capability:
  - `gold.get_price`
- Current path:
  - deterministic direct

### `news`

- Capability:
  - `news.get`
- Current path:
  - deterministic direct

### `search`

- Capability:
  - `search.web`
- Current path:
  - deterministic direct

### `shortlink`

- Capabilities:
  - `shortlink.create`
  - redirect workflow
- Current path:
  - deterministic direct

### `google/calendar`

- action-level workflows:
  - `calendar.help`
  - `calendar.list_today`
  - `calendar.list_tomorrow`
  - `calendar.find_event`
  - `calendar.create_event`
  - `calendar.delete_event`
  - `calendar.check_availability`
- Route intent:
  - help/list -> direct preferred
  - create/delete/find/check -> domain agent path

### `google/gmail`

- action-level workflows:
  - `gmail.help`
  - `gmail.list_inbox`
  - `gmail.read_email`
  - `gmail.search_email`
  - `gmail.send_email`
  - `gmail.draft_email`
  - `gmail.reply_email`
- Route intent:
  - help/inbox -> direct preferred
  - read/search/write/reply -> domain agent path

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

## Compatibility Layer

Các file `*_master.json` trong `google/*` vẫn còn trong repo để:

- giữ tương thích với workflow cũ
- cho phép flow khác gọi bằng text tự nhiên

Nhưng với Mia, hướng đi hiện tại là:

- `mia_core.tools` gọi theo action-level capability
- `Mia: Tool Gateway` route thẳng vào leaf workflow phù hợp
- về lâu dài chỉ giữ `master` nếu thật sự có shared business logic

## Local Structure Direction

```text
n8n/
  docs/
  google/
  langchain_core/
  memory/
  scripts/
    workflow_patches/
  shortlink/
  workflow_*.json
```
