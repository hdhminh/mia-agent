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
- Capability registry and direct-route defaults: [registry.py](../../agent/skills/registry.py)
- Router and planner inference: [router.py](../../agent/brain/router.py) and [planner.py](../../agent/brain/planner.py)
- GitHub request parsing and follow-up routing: [github.py](../../agent/brain/parsers/github.py) and [github_handler.py](../../agent/skills/github_handler.py)
- Web URL request parsing and fetch strategy handling: [web.py](../../agent/skills/web.py), [routes.py](../../agent/skills/web_service/routes.py), and [service.py](../../agent/skills/web_service/service.py)
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
- `web.read_url`
  - args: `url`, `instruction`, `fetchStrategy`, `max_chars`
- `web.summarize_url`
  - args: `url`, `instruction`, `fetchStrategy`, `max_chars`
- `web.ask_url`
  - args: `url`, `question`, `instruction`, `fetchStrategy`, `max_chars`
- `shortlink.create`
  - args: `url`, `ttl`
- `memory.search`
  - args: `query`, `memory_type`, `limit`, `threshold`
- `memory.recent`
  - args: `limit`
- `memory.write`
  - args: `content`, `memory_type`, `title`, `tags`, `importance`

### 2. Structured GitHub Capabilities

These map cleanly to `tool + args` and should stay direct whenever possible.

- `github.list_user_repos`
  - args: `username`, `visibility`, `limit`, `page`, `instruction`
- `github.search_repos`
  - args: `query`, `topic`, `language`, `sortBy`, `limit`, `page`, `instruction`
- `github.get_repo`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `instruction`
- `github.get_repo_tree`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `path`, `ref`, `limit`, `instruction`
- `github.list_branches`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `limit`, `instruction`
- `github.list_commits`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `ref`, `limit`, `instruction`
- `github.get_commit`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `ref`, `instruction`
- `github.get_file`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `path`, `ref`, `maxChars`, `instruction`
- `github.search_code`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `query`, `limit`, `instruction`
- `github.get_diff`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `base`, `head`, `instruction`
- `github.list_releases`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `limit`, `instruction`
- `github.get_release`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `tag`, `releaseId`, `instruction`
- `github.list_pull_requests`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `state`, `limit`, `page`, `instruction`
- `github.get_pull_request`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `number`, `instruction`
- `github.list_issues`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `state`, `labels`, `limit`, `page`, `instruction`
- `github.get_issue`
  - args: `repo`, `owner`, `repoName`, `repoUrl`, `number`, `instruction`

### 3. Partially Structured Search/List Capabilities

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

### 4. Legacy Instruction-Driven Actions

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
5. Keep web URL read/ask, Google Maps lookups, and GitHub browse flows structured so the graph stays token-efficient.

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
- Stage 12:
  - `gmail.reply_email` gateway now preserves `messageId`, `searchQuery`, and `body`
  - direct structured replies no longer collapse back to a text-only gateway payload
  - when only a name/query is supplied, these workflows return `ok:false` with plain guidance instead of searching and mutating an arbitrary first result

- Stage 12:
  - `web.read_url`, `web.summarize_url`, and `web.ask_url` now carry `fetchStrategy` end-to-end through planner, gateway, and sub-workflow normalization
  - GitHub follow-ups now cover releases, pull requests, and issues in both direct routing and selected-repo follow-up flows
  - evaluator now fails GitHub/Web specialist responses that do not bring back tool evidence

- Stage 13:
  - `gmail.send_email` and `gmail.draft_email` now preserve structured `to`, `subject`, `body`, `cc`, and `bcc` through gateway and Gmail leaf workflows
  - Gmail send/draft flows still keep instruction compatibility, but structured fields now take effect in the actual n8n Gmail node instead of stopping at the wrapper/gateway layer

- Stage 14:
  - Drive gateway contracts now preserve structured identifiers and target fields for the remaining common legacy actions:
    - `drive.get_file_info`
    - `drive.create_folder`
    - `drive.download_file`
    - `drive.share_file`
    - `drive.move_file`
    - `drive.rename_file`
    - `drive.copy_file`
    - `drive.delete_file`
    - `drive.delete_folder`
    - `drive.export_file`
  - This keeps instruction fallback for compatibility, but the gateway now forwards the exact structured fields that existing Drive leaf workflows already know how to consume
  - Result: less dependence on free-text parsing at the boundary, lower token pressure for follow-up actions, and a cleaner contract without changing the n8n execution architecture

- Stage 15:
  - `gmail.search_email` now preserves structured `query`, `sender`, `subject`, and `limit` through planner direct-routing, gateway payload shaping, and Gmail search leaf parsing
  - structured Gmail search filters no longer disappear at the gateway boundary when the request skips the tool wrapper path
  - `drive.search_file` now preserves structured `query`, `mimeType`, `folderId`, and `limit` through planner direct-routing and Drive search leaf parsing via `args`
  - structured Drive search filters no longer fall back to a query-only path when the request bypasses the wrapper layer
  - Docs gateway contracts now preserve the structured fields already supported by the Google Docs leaf workflows:
    - `docs.read_doc`
    - `docs.create_doc`
    - `docs.append_doc`
    - `docs.delete_doc`
  - Sheets gateway contracts now preserve the structured fields already supported by the Google Sheets leaf workflows:
    - `sheets.read_sheet`
    - `sheets.create_sheet`
    - `sheets.append_row`
    - `sheets.update_cell`
    - `sheets.delete_sheet`
  - This keeps instruction fallback for backward compatibility, but follow-up actions can now carry IDs, names, ranges, tabs, values, and content directly through the gateway instead of re-deriving them from free text
  - Result: better token efficiency for multi-step Google Docs/Sheets tasks and fewer edge re-parses at the execution boundary

- Stage 16:
  - Calendar gateway contracts now preserve the structured fields already supported by the Google Calendar leaf workflows:
    - `calendar.find_event`
    - `calendar.create_event`
    - `calendar.delete_event`
    - `calendar.check_availability`
  - This keeps instruction fallback for backward compatibility, but follow-up actions can now pass query/date windows, explicit event IDs, and direct start/end datetimes through the gateway instead of rebuilding them from free text every time
  - Result: leaner multi-step calendar interactions, lower token pressure for follow-ups, and less ambiguity at the n8n execution boundary

- Stage 17:
  - The last two compatibility-heavy Drive gateway actions now preserve the structured fields already supported by their leaf workflows:
    - `drive.create_file`
    - `drive.upload_file`
  - `drive.create_file` now forwards structured `fileName` / `name`, `content`, `mimeType`, and `folderId` / `parentId`
  - `drive.upload_file` now forwards structured `telegramFileId` / `fileId`, `fileName`, `mimeType`, and `folderId`
  - This keeps instruction fallback for backward compatibility, but the final remaining Drive gateway actions no longer stop at raw free-text when structured fields are already available
  - Result: the Google gateway surface is now broadly structured across Calendar, Gmail, Drive, Docs, and Sheets, with legacy parsing pushed mostly into compatibility handling inside leaf workflows

- Stage 18:
  - Planner direct-arg building now stops defaulting to `instruction` when it already has meaningful structured Google args for the migrated surfaces
  - Google tool wrappers now only send `instruction` to the gateway as a compatibility fallback, instead of attaching it by default even when structured fields are already present
  - This applies across the migrated Calendar / Gmail / Drive / Docs / Sheets actions covered in Phase 5
  - Result: lower token overhead in the agent-to-tool path itself, not just at the gateway boundary, while still preserving safe fallback behavior when only natural-language input is available

- Stage 19:
  - The remaining Google search/update wrappers were also moved to structured-first payloads, so they no longer attach `instruction` by default when the agent already has concrete args
  - This now includes the remaining agent-side surfaces such as:
    - `calendar.find_free_slot`
    - `calendar.reschedule_event`
    - `gmail.search_email`
    - `gmail.search_by_sender`
    - `gmail.mark_read`
    - `gmail.archive`
    - `drive.search_file`
    - `docs.search_doc`
    - `docs.update_doc`
    - `sheets.search_sheet`
    - `sheets.update_range`
  - Result: Phase 5 is now structured-first not just at the gateway and planner core, but across nearly the full Google tool-wrapper layer as well

- Stage 20:
  - The gateway now routes the remaining Phase 5 Google actions that had already been exposed at the agent layer but were not yet wired end-to-end through `workflow_mia_tool_gateway.json`
  - Added structured gateway support for:
    - `calendar.find_free_slot`
    - `calendar.reschedule_event`
    - `gmail.search_by_sender`
    - `gmail.mark_read`
    - `gmail.archive`
    - `docs.update_doc`
    - `sheets.update_range`
  - For the leaf workflows that exist only as local JSON artifacts without a fixed deployed workflow ID in the gateway map, routing now uses the gateway's existing `workflowLookup` / `workflowName` path instead of introducing new hardcoded IDs
  - `gmail.search_by_sender` intentionally reuses the existing `gmail.search_email` execution workflow because that leaf workflow already supports structured `sender`, `query`, and `subject` filters
  - Result: the remaining Phase 5 Google actions are now wired through the current architecture without adding a new orchestration shape, while keeping deploy maintenance lower and preserving token-efficient structured payloads

- Stage 21:
  - `sheets.read_range` now follows the same structured-first pattern as the other migrated Google wrappers and planner direct args, so it no longer adds `instruction` by default when `spreadsheetId` / `sheetName` / `range` are already known
  - The Gmail read-email leaf workflow now prefers a direct `messageId` execution path instead of re-searching by free text when the agent already has the exact Gmail message ID
  - The Gmail read formatter now also extracts `text/plain` content from the Gmail API payload body, so the direct-ID path stays useful instead of falling back to snippet-only output
  - Result: Phase 5 removes another common token-wasting re-search path and tightens a previously mixed structured/text execution edge without changing the n8n deployment model

- Stage 22:
  - The Drive delete-file leaf workflow now consumes the structured aliases that the gateway already forwards, instead of acting as if only `fileId` / `fileName` existed
  - `drive.delete_file` now accepts and preserves:
    - `targetId` as the direct file identifier alias
    - `targetName` as the direct display/search alias
    - `folderId` for narrowing fallback search when only a name is available
  - The leaf search/resolve path now keeps `targetId` / `targetName` consistent through execution, so the structured contract survives deeper into the n8n layer
  - Result: another Drive action now benefits from the structured gateway contract in practice, not just on paper, while still retaining backward-compatible raw-text fallback behavior

- Stage 23:
  - The Drive move-file leaf workflow now prefers the structured `targetName` / `targetFolderName` aliases that the gateway can already forward, instead of depending only on `fileName` and raw command parsing
  - The Drive rename-file leaf workflow now also prefers `targetName` as the file lookup alias and preserves `targetName` through the resolve path, so rename behaves correctly when the agent already has a structured target label
  - Result: the Drive execution layer is now less brittle for exact-ID and exact-name flows, and fewer requests need to re-derive their target from free text before they can do useful work

- Stage 24:
  - The Drive share-file and copy-file paths now preserve `targetName` all the way from planner and skill wrapper to gateway and leaf workflow, so the agent can keep a structured file label even when the caller does not speak in the legacy `fileName` vocabulary
  - The Drive copy-file path also carries `targetFolderName` metadata through the same structured contract, without changing the existing n8n copy execution shape or adding a new orchestration branch
  - Result: another chunk of legacy instruction dependence is removed from the Drive surface, while token efficiency and maintainability stay aligned with the current architecture

- Stage 25:
  - The remaining Drive leaf workflows that were still missing top-level workflow names now have proper `Sub-workflow: Google Drive - ...` metadata again, which keeps validation and n8n UI alignment clean
  - `drive.create_folder` now has a structured-args regression test at the wrapper layer, so this basic Drive action stays token-efficient instead of silently drifting back to instruction-only behavior
  - Result: the Drive surface is cleaner to maintain, easier to validate, and a little less dependent on free-text fallbacks for common actions

- Stage 26:
  - `docs.update_doc` now preserves `targetId` / `targetName` from planner to the leaf workflow, so the direct-ID and search-by-title paths stay structured when those aliases already exist
  - The Docs update surface now mirrors the same structured-first contract as the rest of Phase 5 without changing the current n8n deployment model or adding new orchestration shape
  - Result: one more legacy instruction fallback is removed from the Docs surface, which improves token efficiency and keeps maintenance consistent with the existing architecture

- Stage 27:
  - The remaining Docs direct-args paths now preserve structured aliases more consistently across `docs.search_doc`, `docs.read_doc`, `docs.create_doc`, `docs.append_doc`, and `docs.delete_doc`
  - `targetName` is now carried through the planner for Docs title/name lookups, while `targetId` is preserved for the exact-ID append/delete/update paths and `targetFolderId` is preserved for Docs creation
  - Result: the Docs surface relies less on legacy free-text instruction fallback and more on compact structured payloads, which keeps token efficiency high without changing the current n8n workflow shape

- Stage 28:
  - The Google Docs skill wrappers now accept `targetName`, `targetId`, and `targetFolderId` aliases where they matter, so structured inputs can flow from the agent edge without needing to be rephrased as legacy text
  - This keeps the wrapper layer aligned with the planner and n8n leaf workflows, which reduces token waste and makes the Docs surface easier to extend without changing the current deployment model
  - Result: one more chunk of legacy instruction dependence is removed at the skill boundary itself, not just in the planner

- Stage 29:
  - The GitHub browse tools now keep `instruction` out of the payload whenever repo / branch / commit / release / PR / issue / file / code-search fields are already structured, so the planner and skill layer stay compact
  - This applies across the GitHub browse surfaces that phase 5 expands, while preserving the existing GitHub master workflow and not introducing a new orchestration shape
  - Result: another large legacy instruction path is removed from the agent edge, and token usage stays more efficient on the GitHub browse route

- Stage 30:
  - `sheets.update_range` now carries `targetId` / `targetName` / `rangeName` through the planner, skill wrapper, and leaf workflow, so update-range can stay structured when the sheet identity is already known
  - The Sheets update-range surface no longer needs to fall back to legacy instruction text just to pass the sheet label and range through the pipeline
  - Result: one more write path is now aligned with the structured-first contract, which improves token efficiency without changing the current n8n workflow shape

- Stage 31:
  - `gmail.read_email` now preserves structured read context through the planner, skill wrapper, and gateway build, including `messageId`, `query`, `sender`, and `subject`
  - This aligns the direct Gmail read path with the message-ID-first leaf workflow that already existed, instead of forcing the upstream layers to behave like they only had free text
  - Result: another token-wasting re-search path is reduced, and Gmail direct reads stay more faithful to the current structured contract without changing the n8n architecture

The remaining heavy legacy areas are now concentrated mostly in:
- leaf workflow parsing itself still exists for backward compatibility even when planner, tool wrappers, and gateway contracts are now structured across Calendar, Docs, Sheets, Gmail, and most Drive actions
- some Google write/read flows still accept many alias names for compatibility, which is useful today but still broader than an ideal minimal contract
- optional exact-ID success-path tests for write/delete actions, which should only run against disposable fixtures
