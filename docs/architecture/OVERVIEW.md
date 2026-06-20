# Architecture Overview: Mia Agent

Mia is an autonomous AI agent for personal productivity. It is designed to act as your digital assistant, executing actions across various services like Google, GitHub, media, and long-term memory.

The system is split into two primary layers:
1. **Agent Core (Python/LangChain)**: The reasoning engine that routes intents, plans execution, handles conversational state, manages long-term memory, and orchestrates tasks.
2. **Execution Layer (n8n)**: The action runtime that executes the integrations and interfaces with external APIs.

---

## 1. Main Runtime Flow

The diagram below represents the complete flow of an request made by a user:

```text
User (Telegram)
   │
   ▼
n8n: Mia Main Gateway
  - Normalize Telegram input
  - Send POST /mia/chat to Agent Core
   │
   ▼
Agent Core (FastAPI / LangGraph)
  - Settings validation
  - MiaAgentService Orchestrator
  - Ingress Node: Check for confirmations, follow-ups
  - Router: Analyze request and select execution path
   │
   ├───────────────────────────────┐
   │                               │
   ▼ (Deterministic Direct Path)   ▼ (Domain / Agentic Path)
DirectExecutor                   LangGraph Specialist Node
  - Fast execution for cheap,      - LangChain agent executing domain tools
    read-only/deterministic tasks  - History trim & retry middlewares
  - Maps to: weather, gold,        - Maps to: calendar, gmail, drive, docs,
    news, search, shortlinks         sheets, github, media, google_full
   │                               │
   └───────────────┬───────────────┘
                   │
                   ▼ (HTTP request)
n8n Tool Gateway Webhook
  - Auth token verification
  - Maps capability string (e.g. `gmail.send_email`) to leaf workflow
  - Runs execution workflow & returns normalized response
   │
   ▼
Response Normalizer (Agent Core)
  - Sanitize markdown text
  - Recover/cap links
  - Enforce formatting rules
   │
   ▼ (HTTP response)
n8n Main Gateway
  - Formats output message
  - Send message to Telegram
```

---

## 2. Core Domains & Capabilities

Mia is structured around functional domains. Every domain contains action-level workflows exposed as capabilities.

### Memory Domain
- **Implementation**: `agent/memory/repository.py`
- **Capabilities**:
  - `memory_search`: Search long-term vector database (PostgreSQL + pgvector).
  - `memory_recent`: List recently saved memories.
  - `memory_write`: Store new durable memories.
- **Workflow Support**: `execution/integrations/memory/` containing write, search, and recent workflows.

### Google Calendar Domain
- **Capabilities**:
  - `calendar.list_today`: List today's events.
  - `calendar.list_tomorrow`: List tomorrow's events.
  - `calendar.find_event`: Search event by query.
  - `calendar.create_event`: Book a new event.
  - `calendar.delete_event`: Cancel an event.
  - `calendar.check_availability`: Check free/busy slots.

### Gmail Domain
- **Capabilities**:
  - `gmail.list_inbox`: List recent emails.
  - `gmail.search_email`: Search emails by sender/subject/text.
  - `gmail.read_email`: Read full content of an email.
  - `gmail.send_email`: Send an email.
  - `gmail.draft_email`: Draft an email.
  - `gmail.reply_email`: Reply to an email thread.

### Google Drive & Workspace Domain
- **Capabilities**:
  - `drive.list_files`: List files in Google Drive.
  - `drive.search_file`: Search files by query.
  - `drive.create_folder`: Create folder.
  - `docs.read_doc` / `docs.write_doc`: Read/Write Google Docs.
  - `sheets.read_sheet` / `sheets.append_row` / `sheets.update_cell`: Interact with Google Sheets.

### GitHub Domain
- **Capabilities**:
  - `github.get_repo`: Fetch repo information.
  - `github.get_file`: Read file contents.
  - `github.search_code`: Search code in repo.
  - `github.get_diff`: View code diff.

### Media Domain
- **Capabilities**:
  - `image_ocr`: Read text from image.
  - `image_describe`: Describe image contents.
  - `document_summarize`: Summarize PDFs or DOCX files.
  - `audio_transcribe`: Transcribe speech to text.
  - `tts_speak`: Convert text to speech.
