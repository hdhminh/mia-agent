# Mia Agent Overview

## 1. Agent Architecture

```text
Telegram User
   |
   v
n8n: Mia Main Gateway
  - normalize Telegram input
  - call POST /mia/chat
   |
   v
mia-core (FastAPI)
  - Settings
  - MiaAgentService
  - ChatOpenAI model
  - MemoryRepository
  - PostgresSaver checkpoint
  - N8nToolGatewayClient
   |
   +------------------------------+
   |                              |
   | direct route                 | full agent loop
   |                              |
   v                              v
n8n Tool Gateway              LangChain create_agent(...)
  - auth token                - toolset by domain
  - map tool -> workflow      - tool calling
  - execute workflow          - history trim middleware
  - normalize tool result     - retry middleware
   |                              |
   v                              v
Domain workflows              Tools
  - weather                      - memory_search/recent/write
  - gold                         - weather/news/search/shortlink
  - news                         - gmail/calendar/drive/docs/sheets
  - search                    (mostly call n8n Tool Gateway)
  - gmail
  - calendar
  - drive
  - docs
  - sheets
  - shortlink
   |
   v
Tool result text
   |
   v
mia-core response
   |
   v
n8n: sendMessage -> Telegram
```

## 2. Agent Flow

```text
1. User sends a Telegram message
   |
   v
2. n8n Mia Main Gateway
   - normalize chatId, rawText, metadata
   - send request to /mia/chat
   |
   v
3. mia-core receives MiaChatRequest
   - build MiaContext
   - resolve thread_id and request_id
   |
   v
4. Fast intent hint
   - _tool_hint_for_request(...)
   |
   +--> 4a. direct-route eligible?
   |       - yes
   |       - and not obviously multi-step
   |          |
   |          v
   |       call n8n Tool Gateway directly
   |       get tool text
   |       sanitize response
   |       return to n8n
   |
   +--> 4b. otherwise use full agent
           |
           v
5. Choose toolset
   - general / calendar / gmail / workspace / google_full
   |
   v
6. Agent invoke
   - system prompt
   - optional tool hint system message
   - current user message
   - thread_id checkpoint
   - history trim middleware
   |
   v
7. Agent behavior
   - answer directly if no tool needed
   - or call one/more tools
   - tools mostly call n8n Tool Gateway
   |
   v
8. Tool result comes back into agent state
   |
   v
9. Finalization
   - sanitize final text
   - fallback summarize if tool was used but final answer is empty
   - prefer tool truth for some cases
   - re-attach missing links, max 3
   |
   v
10. mia-core returns MiaChatResponse
    |
    v
11. n8n formats final text and sends Telegram message
```

## Notes

- Direct route is the cheap, fast path for obvious requests.
- Full agent is used for harder, multi-step, or less certain requests.
- `thread_id = telegram:<chatId>` keeps continuity, but history is trimmed before model calls.
- Memory tools are partly local (`memory_*`) while most external capabilities go through the n8n Tool Gateway.
