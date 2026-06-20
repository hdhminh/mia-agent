# Setup & Deployment Guide

This guide explains how to deploy and configure the Mia Agent stack.

---

## 1. Prerequisites

Make sure your machine has the following tools installed:
- Docker and Docker Compose (v2+)
- Python 3.12+ (for local development)

---

## 2. Configuration (`.env`)

Copy the example environment file and fill in your keys:
```bash
cp .env.example .env
```

### Essential Variables

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token for the Telegram bot interface. |
| `TELEGRAM_ADMIN_CHAT_ID` | Telegram chat ID for the admin user. |
| `OPENROUTER_API_KEY` | OpenRouter key (primary LLM provider). |
| `DEEPSEEK_API_KEY` | DeepSeek API key (optional fallback model). |
| `GROQ_API_KEY` | Groq key for Speech-to-Text and TTS. |
| `MIA_POSTGRES_URI` | PostgreSQL URI connection string (defaults to internal container). |
| `MIA_TOOL_GATEWAY_TOKEN` | Shared secret token to authenticate Python Agent Core -> n8n. |
| `MIA_CORE_API_TOKEN` | Shared secret token to authenticate n8n -> Python Agent Core. |

---

## 3. Launching Services with Docker

Run the entire stack in the background:
```bash
docker compose -f infra/docker-compose.yml up -d --build
```

This starts four core containers:
1. `n8n`: The integration execution layer (runs on port `5678`).
2. `postgres`: Stores user conversation checkpoints, learning insights, and long-term memory.
3. `memory-embedder`: Serves semantic embeddings for text storage (runs on port `8010`).
4. `mia-core`: The FastAPI Python agent engine (runs on port `8000`).

---

## 4. Synchronizing Workflows to n8n

After n8n has started, import the Gateway and Integration workflows from the `execution/` directory:
```bash
# Sync the Tool Gateway workflow
python scripts/maintenance/sync_workflows.py execution/gateway/workflow_mia_tool_gateway.json

# Sync other integration workflows as needed
python scripts/maintenance/sync_workflows.py execution/integrations/google/calendar/workflow_sub_google_calendar_master.json
```
