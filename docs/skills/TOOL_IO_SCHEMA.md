# Mia Tool I/O Schema

## Goal

Every capability should converge toward the same gateway contract:

```json
{
  "tool": "domain.action",
  "args": {},
  "chatId": "telegram_chat_id",
  "userId": "stable_user_id",
  "requestId": "uuid",
  "deliveryMode": "return"
}
```

The normalized result shape should converge toward:

```json
{
  "ok": true,
  "tool": "domain.action",
  "text": "user-facing plain text",
  "result": {},
  "links": [],
  "meta": {}
}
```

## Current Runtime Source of Truth

- Request payload assembly: [execution_client.py](../../agent/execution_client.py)
- Tool bindings: [tools.py](../../agent/skills/tools.py)
- Capability/route grouping: [registry.py](../../agent/skills/registry.py)
- Gateway workflow: [workflow_mia_tool_gateway.json](../../execution/gateway/workflow_mia_tool_gateway.json)

## Capability Classes

### 1. Fully Structured Simple Capabilities

These already map well to `tool + args` and should remain deterministic/direct whenever possible.

- `weather.get`
  - args: `location`
- `gold.get_price`
  - args: none
- `news.get`
  - args: `topic`
- `search.web`
  - args: `query`
- `shortlink.create`
  - args: `url`, `ttl`
- `memory.search`
  - args: `query`, `memory_type`, `limit`, `threshold`
- `memory.recent`
  - args: `limit`
- `memory.write`
  - args: `content`, `memory_type`, `title`, `tags`, `importance`

### 2. Partially Structured Search/List Capabilities

These already have a structured core, but some flows still carry an `instruction` fallback for compatibility.

- `gmail.search_email`
  - current args: `query`, `instruction`
  - target args: `query`, `sender`, `subject`, `limit`
- `drive.search_file`
  - current args: `query`, `fileName`, `mimeType`, `limit`, optional `instruction`
  - target args: `query`, `file_name`, `mime_type`, `folder_id`, `limit`
- `docs.search_doc`
  - current args: `query`, `docName`, `limit`
  - target args: `query`, `doc_name`, `folder_id`, `limit`
- `sheets.search_sheet`
  - current args: `query`, `sheetName`, `limit`
  - target args: `query`, `sheet_name`, `folder_id`, `limit`
- `drive.list_files`
  - current args: mostly empty/direct defaults
  - target args: `limit`, `folder_id`, `mime_type`
- `gmail.list_inbox`
  - current args: mostly empty/direct defaults
  - target args: `limit`, `label`, `unread_only`
- `calendar.list_today`
  - current args: empty
  - target args: `calendar_id`, `limit`, `timezone`
- `calendar.list_tomorrow`
  - current args: empty
  - target args: `calendar_id`, `limit`, `timezone`
- `calendar.check_availability`
  - current args: `date`, `startAt`, `endAt`, `calendarId`, optional `instruction`
  - target args: `date`, `start_at`, `end_at`, `timezone`, `calendar_id`
- `calendar.delete_event`
  - current args: `eventId`, `query`, `calendarId`, optional `instruction`
  - target args: `event_id`, optional `query`, `calendar_id`
- `gmail.read_email`
  - current args: `query`, `messageId`, optional `instruction`
  - target args: `query`, optional `message_id`
- `gmail.draft_email`
  - current args: `to`, `subject`, `body`, optional `instruction`
  - target args: `to`, `subject`, `body`, optional `cc`, `bcc`
- `gmail.reply_email`
  - current args: `searchQuery`, `messageId`, `body`, optional `instruction`
  - target args: `message_id`, `body`, optional `search_query`, `reply_all`

### 3. Legacy Instruction-Driven Actions

These still rely mainly on free-text `instruction` and should be migrated next.

- `calendar.find_event`
- `calendar.create_event`
- `gmail.send_email`
- `drive.get_file_info`
- `drive.create_folder`
- `drive.create_file`
- `drive.download_file`
- `drive.share_file`
- `drive.move_file`
- `drive.rename_file`
- `drive.copy_file`
- `drive.delete_file`
- `drive.delete_folder`
- `drive.export_file`
- `docs.read_doc`
- `docs.create_doc`
- `docs.append_doc`
- `docs.delete_doc`
- `sheets.read_sheet`
- `sheets.create_sheet`
- `sheets.append_row`
- `sheets.update_cell`
- `sheets.delete_sheet`

## Migration Targets for Legacy Actions

### Calendar

- `calendar.find_event`
  - target args: `query`, `date_from`, `date_to`, `calendar_id`, `limit`
- `calendar.create_event`
  - target args: `title`, `start_at`, `end_at`, `timezone`, `location`, `description`, `calendar_id`
- `calendar.delete_event`
  - target args: `event_id`, optional `query`
- `calendar.check_availability`
  - target args: `date`, `date_from`, `date_to`, `timezone`, `calendar_id`

### Gmail

- `gmail.read_email`
  - target args: `message_id`
- `gmail.send_email`
  - target args: `to`, `subject`, `body`, `cc`, `bcc`
- `gmail.draft_email`
  - target args: `to`, `subject`, `body`, `cc`, `bcc`
- `gmail.reply_email`
  - target args: `message_id`, `body`, `reply_all`

### Drive

- `drive.get_file_info`
  - target args: `file_id`
- `drive.create_folder`
  - target args: `name`, `parent_id`
- `drive.create_file`
  - target args: `name`, `content`, `mime_type`, `parent_id`
- `drive.upload_file`
  - target args: `file_id` or `telegram_file_id`, optional `file_name`, `mime_type`, `folder_id`
- `drive.download_file`
  - target args: `file_id`
- `drive.share_file`
  - target args: `file_id`, `email`, `role`
- `drive.move_file`
  - target args: `file_id`, `target_folder_id`
- `drive.rename_file`
  - target args: `file_id`, `new_name`
- `drive.copy_file`
  - target args: `file_id`, `new_name`, `parent_id`
- `drive.delete_file`
  - target args: `file_id`
- `drive.delete_folder`
  - target args: `folder_id`
- `drive.export_file`
  - target args: `file_id`, `target_mime_type`

### Docs

- `docs.read_doc`
  - target args: `document_id`, `max_chars`
- `docs.create_doc`
  - target args: `title`, `content`, `folder_id`
- `docs.append_doc`
  - target args: `document_id`, `content`
- `docs.delete_doc`
  - target args: `document_id`

### Sheets

- `sheets.read_sheet`
  - target args: `spreadsheet_id`, `sheet_name`, `range`, `max_rows`
- `sheets.create_sheet`
  - target args: `title`, `sheet_name`
- `sheets.append_row`
  - target args: `spreadsheet_id`, `sheet_name`, `values`
- `sheets.update_cell`
  - target args: `spreadsheet_id`, `sheet_name`, `cell`, `value`
- `sheets.delete_sheet`
  - target args: `spreadsheet_id`

## Output Normalization Rules

- `text`
  - plain Vietnamese, no HTML, no markdown
  - user-facing, concise
- `links`
  - separate URL array when available
  - final response should expose at most `3` links
- `result`
  - structured payload for future router/domain-agent use
- `meta`
  - optional machine-facing metadata such as ids, timestamps, source names

## Immediate Refactor Priority

1. Keep simple capabilities structured and deterministic.
2. Remove `instruction` from search/list flows where args already exist.
3. Finish migrating remaining Google write/read actions from free-text `instruction` to action-specific args.
4. Make the gateway normalize all workflow outputs to the same `ok/text/result/links/meta` contract.

## Latest Implemented Progress

- Stage 1:
  - `gmail.search_email`
  - `docs.search_doc`
  - `drive.search_file`
  - `sheets.search_sheet`
  - `calendar.create_event`
  - `gmail.send_email`
- Stage 2:
  - `drive.get_file_info`
  - `drive.create_folder`
  - `drive.delete_file`
  - `drive.share_file`
  - `docs.read_doc`
  - `docs.create_doc`
  - `docs.append_doc`
  - `docs.delete_doc`
  - `sheets.read_sheet`
  - `sheets.create_sheet`
  - `sheets.append_row`
  - `sheets.update_cell`
  - `sheets.delete_sheet`
- Stage 3:
  - `calendar.delete_event`
  - `calendar.check_availability`
  - `gmail.read_email`
  - `gmail.draft_email`
  - `gmail.reply_email`
- Stage 4:
  - `drive.create_file`
  - `drive.download_file`
  - `drive.move_file`
  - `drive.rename_file`
  - `drive.copy_file`
  - `drive.delete_folder`
  - `drive.export_file`
- Stage 5:
  - `calendar.find_event`
  - `gmail.send_email` richer structured field handling
- Stage 6:
  - `drive.upload_file`
  - `drive.upload_file` local workflow repaired to use structured Telegram file metadata and return plain-text output
- Stage 7:
  - `gmail.search_email`
  - `gmail.read_email`
  - `calendar.find_event`
  - `calendar.check_availability`
  - `docs.read_doc`
  - `sheets.read_sheet`
  - `workflow_mia_tool_gateway` now normalizes plain text, result, metadata and caps visible links to `3`
  - `mia-core` response normalizer also caps final visible links to `3`
- Stage 8:
  - `docs.read_doc` and `sheets.read_sheet` no-result branches now return structured text instead of empty n8n executions
  - direct tool calls now preserve `ok:false + text` as a valid user-facing result, avoiding unnecessary agent fallback
- Stage 9:
  - Google leaf workflows now route empty IF branches to a structured `Return Empty Branch` node instead of ending with no item
  - missing input / not-found paths return `ok:false`, plain `text`, empty `links`, `result`, and explanatory `meta`
- Stage 10:
  - `gmail.reply_email` no longer sends a reply from a search query alone
  - reply requires a concrete `messageId`, preventing accidental replies to the latest email
- Stage 11:
  - high-risk Google mutations now require concrete IDs instead of acting on the first search result
  - guarded actions:
    - `calendar.delete_event`
    - `docs.append_doc`
    - `docs.delete_doc`
    - `drive.copy_file`
    - `drive.delete_file`
    - `drive.delete_folder`
    - `drive.move_file`
    - `drive.rename_file`
    - `drive.share_file`
    - `sheets.append_row`
    - `sheets.delete_sheet`
    - `sheets.update_cell`
  - when only a name/query is supplied, these workflows return `ok:false` with plain guidance instead of searching and mutating an arbitrary first result

The remaining heavy legacy areas are now concentrated mostly in:
- `gmail.send_email` deeper support/validation for richer fields like `cc/bcc`
- `drive` actions still carrying instruction fallback for compatibility even after structured fields were added
- optional exact-ID success-path tests for write/delete actions, which should only run against disposable fixtures
