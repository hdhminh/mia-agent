# Platform Upgrade and Rollout

## Before deployment

1. Back up Postgres and export active n8n workflows.
2. Set non-empty, different `MIA_CORE_API_TOKEN` and `MIA_TOOL_GATEWAY_TOKEN`.
3. Configure Google Tasks and Google Contacts OAuth credentials in n8n. Grant
   only the Tasks and People scopes required by the imported workflows.
4. Set a least-privilege `GITHUB_TOKEN` only if GitHub write tools are needed.
5. Review `MIA_WEB_MAX_RESPONSE_BYTES`, `MIA_MEDIA_MAX_INPUT_BYTES`, rate limits,
   and optional read-only `MIA_MCP_SERVERS_JSON` entries.

## Deploy

Run:

```bash
docker compose -f infra/docker-compose.yml up -d --build
python scripts/maintenance/validate_workflow_json.py
python scripts/maintenance/validate_tool_contracts.py
```

Import/sync the gateway plus the Tasks, Contacts, Automation, Media, and GitHub
master workflows. Activate them only after their credentials resolve correctly.
The SQL setup is additive: memory lifecycle fields, approval ownership, execution
journal, skill runs, and scheduler lease fields are created with `IF NOT EXISTS`.

## Smoke checks

- Verify unauthenticated `/mia/chat`, `/mia/feedback`, `/mia/web/*`, and
  `/mia/media/*` requests return 401 or 503.
- Verify read-only tools run immediately and every external write pauses for an
  exact confirmation.
- Repeat the same confirmed request and confirm the execution journal replays it
  instead of duplicating the external change.
- Create a cron automation such as `0 8 * * *`, check `next_run_at`, and verify
  only one instance claims it.
- Inspect `/mia/ops/metrics?days=7` using the core token.

## Rollback

Deploy the previous image and restore the previous n8n workflow exports. The new
database columns and tables are backward-compatible and can remain in place;
avoid destructive schema rollback during an incident.
