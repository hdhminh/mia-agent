# Skill Registry: Capabilities & Tools

Mia Agent's skills represent its action-level capabilities (e.g. read email, send calendar invite). Skills are divided between **Agentic Tools** (called by specialists) and **Deterministic Direct Tools** (called directly without planning).

---

## 1. Capability Mapping

Tool definitions are managed inside `agent/skills/registry.py` (previously `capabilities.py`). 

Tools map capability names to execution webhook triggers handled by n8n.

### Agentic Toolsets
Specialists have distinct tool parameters defined in `AGENT_TOOLSETS`:

- **`general`**:
  - `gold_get_price`
  - `weather_get`
  - `news_get`
  - `search_web`
  - `shortlink_create`
- **`media`**:
  - `image_ocr`
  - `image_describe`
  - `document_summarize`
  - `audio_transcribe`
  - `tts_speak`
- **`calendar`**:
  - `calendar_list_today`
  - `calendar_list_tomorrow`
  - `calendar_find_event`
  - `calendar_create_event`
  - `calendar_delete_event`
  - `calendar_check_availability`
- **`gmail`**:
  - `gmail_list_inbox`
  - `gmail_search_email`
  - `gmail_read_email`
  - `gmail_send_email`
  - `gmail_draft_email`
  - `gmail_reply_email`
- **`workspace`**:
  - `drive_list_files`
  - `drive_search_file`
  - `drive_create_folder`
  - `docs_read_doc`
  - `docs_create_doc`
  - `sheets_append_row`
  - `sheets_update_cell`

---

## 2. Gateway Protocol

When a Python tool is executed, it routes request payload parameters through `N8nToolGatewayClient`:
- **Webhook Endpoint**: `POST /webhook/mia-tool`
- **Authentication**: Bearer Token (`MIA_TOOL_GATEWAY_TOKEN`)
- **JSON Payload Contract**:
  ```json
  {
    "action": "gmail.send_email",
    "args": {
      "to": "recipient@example.com",
      "subject": "Hello",
      "body": "World"
    },
    "context": {
      "chat_id": "12345",
      "user_id": "67890",
      "request_id": "req-xyz",
      "timezone": "Asia/Ho_Chi_Minh"
    }
  }
  ```

---

## 3. How to Add a New Skill

To add a new capability:
1. **Define workflow on n8n web instance**: Create the sub-workflow handling the actual action.
2. **Add schema mapping to n8n Tool Gateway**: Register the mapping inside the Tool Gateway route configuration.
3. **Register Python tool in Agent Core**:
   - Create tool schema in `agent/skills/` (e.g. `agent/skills/simple.py`).
   - Add tool name to `AGENT_TOOLSETS` inside `agent/skills/registry.py` under the appropriate domain.
   - Re-export tool constructor inside `agent/skills/__init__.py`.
