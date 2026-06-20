# Execution Layer

This directory contains n8n workflows that serve as the execution layer for Mia Agent.

The agent core (in `agent/`) decides **what** to do. These workflows execute **how** to do it.

## Structure

- `gateway/` — Tool Gateway (single webhook entry point for all tool calls) and final fix logic
- `integrations/` — Domain-specific workflows (Google Workspace, GitHub, media, weather, news, etc.)
- `monitors/` — Error monitoring and Telegram alert workflows
- `legacy/` — Old legacy workflows being phased out

## Syncing to n8n

Workflows are synced to the n8n web instance using the command-line sync utility:
```bash
python scripts/maintenance/sync_workflows.py execution/gateway/workflow_mia_tool_gateway.json
```
