# Mia Agent Overview

## 1. Router-First Architecture

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
  - Router
  - DirectExecutor
  - ResponseNormalizer
  - ChatOpenAI model
  - MemoryRepository
  - PostgresSaver checkpoint
  - N8nToolGatewayClient
   |
   +---------------------------------------+
   |                                       |
   | deterministic direct path             | domain / agent path
   |                                       |
   v                                       v
DirectExecutor                         LangChain create_agent(...)
  - memory_recent                        - toolset by domain
  - weather                              - tool calling
  - gold                                 - history trim middleware
  - news                                 - retry middleware
  - search
  - shortlink
  - help/list/search read-only flows
   |                                       |
   v                                       v
n8n Tool Gateway                      Tools registry
  - auth token                        - memory_search/recent/write
  - map capability -> workflow        - gmail/calendar/drive/docs/sheets
  - execute workflow                  - simple tools as fallback
  - normalize tool result
   |                                       |
   v                                       v
Domain workflows                      Tool results in agent state
   |                                       |
   +-------------------+-------------------+
                       |
                       v
Response normalizer
  - sanitize text
  - recover missing links
  - enforce max links
  - fallback final text
   |
   v
n8n: sendMessage -> Telegram
```

## 2. Current Agent Flow

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
4. Router decides route
   - detect hint tool
   - detect whether request is deterministic or agentic
   - decide target toolset when agent is needed
   |
   +--> 4a. deterministic direct path
   |       |
   |       v
   |    DirectExecutor
   |    - build structured args
   |    - call n8n Tool Gateway
   |    - return normalized text
   |
   +--> 4b. domain / agent path
           |
           v
5. Select agent toolset
   - general
   - calendar
   - gmail
   - workspace
   - google_full
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
8. Post-processing
   - sanitize final text
   - fallback summarize if model returns empty after tool use
   - prefer tool truth for known failure modes
   - re-attach missing links
   |
   v
9. mia-core returns MiaChatResponse
   |
   v
10. n8n formats final text and sends Telegram message
```

## 3. Current Code Structure

```text
langchain_core/mia_core/
  app.py
  agent.py
  capabilities.py
  request_parser.py
  router.py
  direct_executor.py
  response_normalizer.py
  tools.py
  n8n_client.py
  memory.py
  models.py
  config.py
```

## Notes

- Direct path is now treated as the preferred path for cheap, obvious, read-only or low-side-effect tasks.
- Full agent is reserved for domain-heavy or genuinely multi-step requests.
- `thread_id = telegram:<chatId>` still preserves continuity, but history is trimmed before model calls.
- Memory tools are local; most external capabilities still route through the n8n Tool Gateway.
