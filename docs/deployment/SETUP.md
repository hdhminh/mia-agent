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
| `HOME_ASSISTANT_URL` | Base URL for Home Assistant, recommended `http://host.docker.internal:8123` from the n8n container. |
| `HOME_ASSISTANT_TOKEN` | Home Assistant long-lived access token used by the smart-home workflow. |
| `MIA_HOME_ALLOWED_LABEL` | Home Assistant label name Mia is allowed to control, default `mia_allowed`. |
| `MIA_HOME_DASHBOARD_URL` | Local Lovelace URL shown back to the user, for example `http://192.168.1.10:8123`. |
| `MIA_HOME_DEFAULT_AREA` | Optional default area such as `Phòng ngủ` to bias ambiguous device lookups. |
| `MIA_HOME_ENTITY_ALIASES_JSON` | Optional JSON map from natural nicknames to exact entity IDs. |
| `MIA_HOME_TTS_ENTITY_ID` | Optional TTS provider entity used when Mia speaks through a media player. |
| `MIA_MODEL` / `MIA_DEEPSEEK_MODEL` | Primary model identifiers (OpenRouter / DeepSeek). |
| `MIA_MODEL_MAX_TOKENS` | Max answer tokens (default 1600). Low values truncate long answers. |
| `MIA_REMINDER_QUIET_HOURS` | Suppress scheduled reminders overnight, e.g. `23-7` (default). |
| `MIA_CODE_GATEWAY_URL` / `MIA_CODE_GATEWAY_TOKEN` | OpenCode gateway base URL and bearer secret. |
| `MIA_CODE_WORKSPACE_ROOT` / `MIA_CODE_HOST_WORKSPACE_ROOT` | Container and host paths for managed code workspaces. |
| `MIA_CODE_ALLOWED_COMMAND_PREFIXES` | Bash prefixes OpenCode may run (python/cat/tail/sed/awk are excluded by default). |

---

## 3. Launching Services with Docker

Run the entire stack in the background:
```bash
docker compose -f infra/docker-compose.yml up -d --build
```

This starts the core containers:
1. `n8n`: The integration execution layer (runs on port `5678`).
2. `postgres`: Stores user conversation checkpoints, learning insights, and long-term memory.
3. `memory-embedder`: Serves semantic embeddings for text storage (runs on port `8010`).
4. `mia-core`: The FastAPI Python agent engine (runs on port `8000`).
5. `home-assistant`: Local smart-home dashboard and device hub (host network, usually `8123`).

---

## 4. Synchronizing Workflows to n8n

After n8n has started, import the Gateway and Integration workflows from the `execution/` directory:
```bash
# Sync the Tool Gateway workflow
python scripts/maintenance/sync_workflows.py execution/gateway/workflow_mia_tool_gateway.json

# Sync other integration workflows as needed
python scripts/maintenance/sync_workflows.py execution/integrations/google/calendar/workflow_sub_google_calendar_master.json
python scripts/maintenance/sync_workflows.py --create-missing execution/integrations/homeassistant/workflow_sub_home_assistant_smart_home_master.json
```

## 5. Home Assistant Labeling

For Mia smart-home control:
- Put devices into proper Home Assistant Areas such as `Phòng ngủ` and `Phòng tắm`.
- Add the label `mia_allowed` only to entities Mia may control.
- Optional: configure `MIA_HOME_ENTITY_ALIASES_JSON` for custom nicknames and `MIA_HOME_TTS_ENTITY_ID` for speaker announcements.
- Use `python scripts/maintenance/bootstrap_home_assistant_inventory.py` after you have a token to inspect visible entities and generate alias suggestions.
- Use `python scripts/maintenance/check_smarthome_readiness.py` for a quick end-to-end readiness report.
- If an IR-controlled fan or air-conditioner shows as `unsupported`, prefer exposing Home Assistant `script` or `scene` entities and label those instead of the raw unsupported device.

## 6. Practical Smart-Home Rollout

For the full step-by-step rollout, naming guidance, and bootstrap commands, see [Home Assistant setup](HOME_ASSISTANT_SETUP.md).
