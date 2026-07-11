# Platform Upgrade and Rollout

## Before deployment

1. Back up Postgres and export active n8n workflows.
2. Set non-empty, different `MIA_CORE_API_TOKEN` and `MIA_TOOL_GATEWAY_TOKEN`.
3. Configure Google Tasks and Google Contacts OAuth credentials in n8n. Grant
   only the Tasks and People scopes required by the imported workflows.
4. Set `GOOGLE_MAPS_API_KEY` plus optional `MIA_MAPS_DEFAULT_LANGUAGE`,
   `MIA_MAPS_DEFAULT_REGION`, and `MIA_MAPS_MAX_PLACE_RESULTS`.
5. Set a least-privilege `GITHUB_TOKEN` when GitHub write tools are enabled.
6. Review `MIA_WEB_MAX_RESPONSE_BYTES`, `MIA_MEDIA_MAX_INPUT_BYTES`, rate limits,
   and optional read-only `MIA_MCP_SERVERS_JSON` entries.

## Deploy

Run the core-only compose if `n8n` and Postgres are already running:

```bash
docker compose -f infra/docker-compose.core.yml up -d --build
```

Run the full stack only on a clean host:

```bash
docker compose -f infra/docker-compose.yml up -d --build
python scripts/maintenance/validate_workflow_json.py
python scripts/maintenance/validate_tool_contracts.py
```

Import/sync the gateway plus the Tasks, Contacts, Automation, Media, GitHub,
and Google Maps master workflows. Activate them only after their credentials
resolve correctly.
The SQL setup is additive: memory lifecycle fields, approval ownership, execution
journal, skill runs, and scheduler lease fields are created with `IF NOT EXISTS`.

## Google Maps pricing note

As of July 11, 2026, Google Maps Platform pricing is documented with monthly
free usage caps per SKU instead of the older shared `$200` monthly credit model.
Typical caps shown on the pricing pages are:

- Essentials: `10,000` free billable events per SKU each month
- Pro: `5,000`
- Enterprise: `1,000`
- New accounts also receive a separate `$300` trial credit

Operational advice:

- Keep `MIA_MAPS_MAX_PLACE_RESULTS` low unless there is a strong product need.
- Restrict field masks in Places / Routes calls to the minimum fields required.
- Configure budget alerts in Google Cloud before production traffic.

## Smoke checks

- Verify unauthenticated `/mia/chat`, `/mia/feedback`, `/mia/web/*`, and
  `/mia/media/*` requests return 401 or 503.
- Verify read tools run immediately and every external write pauses for an
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

