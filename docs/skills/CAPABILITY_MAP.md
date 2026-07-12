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
- `time_now`
- `weather_get`
- `gold_get_price`
- `news_get`
- `search_web`
- `read_url`
- `summarize_url`
- `ask_url`
- `shortlink_create`
- `calendar_help`
- `calendar_list_today`
- `calendar_list_tomorrow`
- `calendar_find_event`
- `calendar_check_availability`
- `calendar_find_free_slot`
- `gmail_help`
- `gmail_list_inbox`
- `gmail_read_email`
- `gmail_search_email`
- `gmail_search_by_sender`
- `github_help`
- `github_list_user_repos`
- `github_search_repos`
- `github_get_repo`
- `github_get_repo_tree`
- `github_list_branches`
- `github_list_commits`
- `github_get_commit`
- `github_list_releases`
- `github_get_release`
- `github_list_pull_requests`
- `github_get_pull_request`
- `github_list_issues`
- `github_get_issue`
- `github_get_file`
- `github_search_code`
- `github_get_diff`
- `drive_help`
- `drive_list_files`
- `drive_search_file`
- `docs_help`
- `docs_search_doc`
- `docs_read_doc`
- `sheets_read_range`
- `sheets_help`
- `sheets_search_sheet`
- `sheets_read_sheet`
- `tasks_list`
- `tasks_list_due`
- `tasks_list_overdue`
- `contacts_search`
- `contacts_get`
- `contacts_resolve_recipient`
- `automation_list`
- `smarthome_help`
- `smarthome_list_areas`
- `smarthome_list_devices`
- `smarthome_room_status`

## Domain Agent Candidates

### `calendar`

- `calendar_create_event`
- `calendar_delete_event`
- `calendar_reschedule_event`

### `gmail`

- `gmail_send_email`
- `gmail_draft_email`
- `gmail_reply_email`
- `gmail_mark_read`
- `gmail_archive`

### `github`

- `github_help`
- `github_list_user_repos`
- `github_search_repos`
- `github_get_repo`
- `github_get_repo_tree`
- `github_list_branches`
- `github_list_commits`
- `github_get_commit`
- `github_list_releases`
- `github_get_release`
- `github_list_pull_requests`
- `github_get_pull_request`
- `github_list_issues`
- `github_get_issue`
- `github_get_file`
- `github_search_code`
- `github_get_diff`
- `github_create_issue`
- `github_update_issue`
- `github_comment_issue`
- `github_create_branch`
- `github_update_file`
- `github_create_pull_request`
- `github_comment_pull_request`
- `github_list_workflow_runs`
- `github_rerun_failed_workflow`

### `productivity`

- Google Tasks: list, due, overdue, create, update, complete, delete
- Google Contacts: search, get, resolve recipient candidates
- Automation: list, create, pause, resume, delete, run now

### `smarthome`

- `smarthome_help`
- `smarthome_list_areas`
- `smarthome_list_devices`
- `smarthome_room_status`
- `smarthome_turn_on`
- `smarthome_turn_off`
- `smarthome_toggle`
- `smarthome_set_light`
- `smarthome_set_climate`
- `smarthome_set_fan`
- `smarthome_set_media`
- `smarthome_announce`
- `smarthome_run_scene`

### Reusable Skills

- `daily_briefing`
- `meeting_assistant`
- `research_report`
- `expense_receipt`
- `repository_review`

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
- `docs_update_doc`
- `docs_delete_doc`
- `sheets_read_sheet`
- `sheets_read_range`
- `sheets_create_sheet`
- `sheets_append_row`
- `sheets_update_cell`
- `sheets_update_range`
- `sheets_delete_sheet`

## Current Direction

- Câu rõ ràng + ít side effect phải đi `direct_deterministic`.
- Câu nhiều bước nhưng bản chất chỉ cần `simple capability + style follow-up` vẫn ưu tiên direct path.
- Chỉ các thao tác domain sâu hoặc nhiều side effect mới vào `agentic_domain` / `agentic_multistep`.
