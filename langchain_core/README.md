# Mia LangChain Core

`mia-core` is the new brain for Mia.

Responsibilities:

- run the LangChain agent
- keep short-term memory through LangGraph checkpoints
- store and retrieve long-term memory from Postgres/pgvector
- call n8n through a single tool gateway webhook

The n8n side should keep:

- Telegram trigger and Telegram delivery
- Google integrations
- search/news/weather/gold helper workflows
- operational workflows like schedules and error monitoring

## Environment

- `PRIMARY_LLM_PROVIDER`: `openrouter` or `deepseek_direct`
- `OPENROUTER_API_KEY`: required if using OpenRouter or as DeepSeek fallback
- `DEEPSEEK_API_KEY`: required if `PRIMARY_LLM_PROVIDER=deepseek_direct`
- `MIA_MODEL`: OpenRouter fallback model id, default `deepseek/deepseek-v4-flash`
- `MIA_DEEPSEEK_MODEL`: direct DeepSeek model id, default `deepseek-v4-flash`
- `MIA_POSTGRES_URI`: defaults to the local pgvector container
- `MIA_MEMORY_EMBEDDER_URL`: defaults to `http://memory-embedder:8000/embed`
- `MIA_TOOL_GATEWAY_URL`: defaults to `http://n8n:5678/webhook/mia-tool`
- `MIA_TOOL_GATEWAY_TOKEN`: shared secret with the n8n tool gateway
- `MIA_EVALUATOR_MODE`: evaluator mode (`soft` or `hard`, default `hard`)
- `MIA_EVALUATOR_MAX_RETRIES`: max evaluator retry attempts (default `2`)

## Directory Structure

Under `mia_core/`, the codebase is organized as follows:
- `parsers/`: Submodules for request parsing & normalization (`google.py`, `github.py`, `media.py`, `web.py`, `common.py`). Central orchestrator is `request_parser.py`.
- `tool_defs/`: Submodules defining LangChain tools (`memory.py`, `simple.py`, `google.py`, `github.py`, `media.py`, `web.py`, `common.py`). Exported via `tools.py`.
- `web/`: Runtime web-page fetch/read/summarize service used by `/mia/chat`.
- `media/`: Runtime multimodal analysis service for OCR, document, audio, video, and TTS flows.
- `nodes/`: Agent state graph nodes (e.g. `supervisor.py`).
- `prompts.py`: Central repository for all system instructions and prompts.
- `github_handler.py` & `followup_handler.py`: Decoupled helper classes for executing special GitHub operations and follow-up handlers.

## API

`POST /mia/chat`

```json
{
  "chat_id": "123",
  "text": "mai thời tiết ở Đà Lạt sao",
  "thread_id": "telegram:123",
  "user_id": "123"
}
```

Response:

```json
{
  "final_text": "...",
  "tools_called": ["weather_get"],
  "thread_id": "telegram:123",
  "request_id": "..."
}
```
