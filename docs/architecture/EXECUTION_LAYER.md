# Execution Layer: n8n Workflow Runtime

The execution layer is composed of n8n workflows that serve as the action runtime for Mia. While the Agent Core (in `agent/`) handles **reasoning and decision making**, the Execution Layer (in `execution/`) handles **API orchestration and side effects**.

---

## 1. Directory Structure

```text
execution/
├── gateway/         ⚡ Tool Gateway & Error Fix webhook endpoints
├── integrations/    🔌 Domain action-level leaf workflows
│   ├── google/      - calendar, gmail, drive, docs, sheets, tasks, contacts, maps
│   ├── github/      - GitHub integrations
│   ├── media/       - Media services
│   ├── homeassistant/ - Smart Home master
│   ├── simple/      - news, gold, weather, search, notify telegram
│   ├── web/         - URL read, summarize, ask
│   ├── memory/      - memory write/search/recent
│   ├── automation/  - automation master
│   └── shortlink/   - worker redirect & shortlinks
├── monitors/        🚨 Alerting & monitors
└── legacy/          ⏳ Legacy workflows being phased out
```

---

## 2. Gateway Workflows

All tool executions run through a single unified endpoint:

### Tool Gateway (`workflow_mia_tool_gateway.json`)
Receives execution requests from the Python Agent Core. It:
1. Validates the incoming `x-mia-tool-token` in **constant time** (fails closed when unset).
2. Rejects private/local URLs for `web.read_url` / `web.summarize_url` / `web.ask_url` (SSRF guard).
3. Extracts the `action` identifier (e.g., `calendar.create_event`, `web.read_url`, `github.get_release`, `notify.telegram`).
4. Normalizes the structured args for the selected workflow, including web `fetchStrategy` and GitHub repo context for release / pull request / issue lookups.
5. Dispatches the parameters to the correct leaf integration workflow via an internal `Execute Workflow` node.
6. Gathers outputs, formats them into the stable `ok/text/result/links/meta` contract, and returns them to the Python Agent Core.

All exported workflows carry a 60s timeout on HTTP request nodes and
`continueRegularOutput` on fallible nodes, so external failures surface as a
normal error result instead of hanging silently.

---

## 3. Workflow Sync Mechanism

Workflows are versioned inside git and synchronized to the web n8n instance using maintenance scripts:

### Single Workflow Sync
```bash
python scripts/maintenance/sync_workflows.py execution/gateway/workflow_mia_tool_gateway.json
```

### Auto Sync daemon
`scripts/sync/sync_daemon.sh` (installed hourly in the system cron) validates
every exported workflow with `scripts/sync/auto_sync.py`, which refuses to
commit on the default branch and is dry-run by default.

---

## 4. Design Guidelines for Workflows

When creating new integration workflows:
1. **Always return structured responses**: Ensure the final node outputs a JSON object containing the normalized contract fields (`ok`, `text`, `result`, `links`, `meta`).
2. **Keep logic thin**: Avoid putting complex decision loops or NLP parsing inside n8n. Let the Agent Core plan which workflow to trigger.
3. **Handle errors gracefully**: Put error boundary flags or catch nodes to return a meaningful error message to the gateway rather than raising an unhandled exception.
4. **Preserve token efficiency**: Keep visible link output capped and avoid duplicating text across `text`, `result`, and `meta` unless the data is needed downstream.
