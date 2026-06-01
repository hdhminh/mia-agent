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

- `OPENROUTER_API_KEY`: required if using OpenRouter
- `MIA_MODEL`: model id, default `openai/gpt-4.1-mini`
- `MIA_POSTGRES_URI`: defaults to the local pgvector container
- `MIA_MEMORY_EMBEDDER_URL`: defaults to `http://memory-embedder:8000/embed`
- `MIA_TOOL_GATEWAY_URL`: defaults to `http://n8n:5678/webhook/mia-tool`
- `MIA_TOOL_GATEWAY_TOKEN`: shared secret with the n8n tool gateway

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
