# Mia LangChain Migration

This repo now contains a new main path for Mia:

```text
Telegram
-> workflow_mia_final_fix.json
-> mia-core (FastAPI + LangChain)
-> workflow_mia_tool_gateway.json
-> legacy helper workflows in backend mode
-> final response back to Telegram
```

## What changed

- `workflow_mia_final_fix.json` is now the main gateway only.
- `langchain_core/` contains Mia's real AI core.
- `workflow_mia_tool_gateway.json` is the single entrypoint for tool calls from LangChain into n8n.
- helper workflows stay in n8n, but Mia now consumes their results instead of letting them speak directly to the user.
- `shortlink/workflow_shortlink_create.json` now supports backend mode by returning text when no `chatId` is provided.

## Activation checklist

1. Fill the new env vars from `.env.example`.
2. Build and start containers:

```bash
docker compose up -d --build mia-core memory-embedder postgres n8n cloudflared
```

3. Import or update these workflows in n8n:
   - `workflow_mia_final_fix.json`
   - `workflow_mia_tool_gateway.json`
   - `shortlink/workflow_shortlink_create.json`

4. Keep helper workflows available in the same n8n instance because the tool gateway still delegates to:
   - `workflow_sub_gold.json`
   - `workflow_sub_news.json`
   - `workflow_sub_search.json`
   - `workflow_sub_weather.json`
   - the Google domain workflows already referenced by the current workflow IDs

5. Activate `Mia: Main Gateway` as the primary Telegram workflow.
6. Activate `Mia: Tool Gateway` as the webhook endpoint for tools.

## Notes

- The tool gateway intentionally sends helper workflows an empty `chatId` in `deliveryMode=return` so they return text instead of sending Telegram directly.
- LangChain now sees tool output and writes the final answer itself.
- Long-term memory is now handled inside `mia-core` through Postgres + pgvector.
