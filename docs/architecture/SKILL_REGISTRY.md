# Skill Registry: Capabilities & Tools

Mia Agent's skills represent its action-level capabilities (e.g. read email, send calendar invite). Skills are divided between **Agentic Tools** (called by specialists) and **Deterministic Direct Tools** (called directly without planning).

---

## 1. Capability Mapping

Tool definitions are managed inside `agent/skills/registry.py` (previously `capabilities.py`). 

Tools map capability names to execution webhook triggers handled by n8n.

### Agentic Toolsets
Specialists have distinct tool parameters defined in `AGENT_TOOLSETS`:

- **`general`**:
  - `gold_get_price`, `weather_get`, `news_get`, `search_web`, `shortlink_create`
  - `time_now`, `notify_telegram` + web tools (`read_url`, `summarize_url`, `ask_url`)
- **`code`** (dev agent — code + github tools):
  - `code_create_project`, `code_import_existing_project`, `code_work_on_project`
  - `code_project_status`, `code_project_diff`
  - `code_review_project`, `code_optimize_project`, `code_run_test`, `code_run_lint`, `code_fix_from_issue`
  - `code_apply_to_existing_project`, `code_publish_project` (both require centralized approval)
  - Plus the full `github_*` read/write toolset
- **`media`**:
  - `image_ocr`, `image_describe`, `document_summarize`, `audio_transcribe`, `tts_speak`
- **`calendar`**:
  - `calendar_list_today`, `calendar_list_tomorrow`, `calendar_find_event`
  - `calendar_create_event`, `calendar_delete_event`, `calendar_check_availability`, `calendar_reschedule_event`
- **`gmail`**:
  - `gmail_list_inbox`, `gmail_search_email`, `gmail_read_email`
  - `gmail_send_email`, `gmail_draft_email`, `gmail_reply_email`
- **`workspace`**:
  - Drive, Docs, Sheets, Tasks, Contacts tools (see `registry.py`)
- **`github`**, **`maps`**, **`smarthome`**, **`google_full`**: domain-specific toolsets in `registry.py`

Deterministic direct tools (routed without the agent loop) are listed in
`DETERMINISTIC_DIRECT_TOOLS` and mapped to gateway actions in `DIRECT_GATEWAY_TOOLS`.

---

## 2. Gateway Protocol

When a Python tool is executed, it routes request payload parameters through `N8nToolGatewayClient`:
- **Webhook Endpoint**: `POST /webhook/mia-tool`
- **Authentication**: shared secret via `x-mia-tool-token` header (`MIA_TOOL_GATEWAY_TOKEN`), compared in constant time
- **JSON Payload Contract**:
  ```json
  {
    "tool": "gmail.send_email",
    "args": {
      "to": "recipient@example.com",
      "subject": "Hello",
      "body": "World"
    },
    "chatId": "12345",
    "userId": "67890",
    "requestId": "req-xyz",
    "deliveryMode": "return",
    "text": "raw user request text"
  }
  ```
- The gateway rejects private/local URLs for `web.read_url` / `web.summarize_url` / `web.ask_url` (SSRF guard).
- Dangerous tools create a pending action in `mia_pending_actions` and require explicit user confirmation before execution.

---

## 3. How to Add a New Skill

To add a new capability:
1. **Define workflow on n8n web instance**: Create the sub-workflow handling the actual action.
2. **Add schema mapping to n8n Tool Gateway**: Register the mapping inside the Tool Gateway route configuration.
3. **Register Python tool in Agent Core**:
   - Create tool schema in `agent/skills/` (e.g. `agent/skills/simple.py`).
   - Add tool name to `AGENT_TOOLSETS` inside `agent/skills/registry.py` under the appropriate domain.
   - Re-export tool constructor inside `agent/skills/__init__.py`.
