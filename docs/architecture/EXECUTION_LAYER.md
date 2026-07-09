# Execution Layer: n8n Workflow Runtime

The execution layer is composed of n8n workflows that serve as the action runtime for Mia. While the Agent Core (in `agent/`) handles **reasoning and decision making**, the Execution Layer (in `execution/`) handles **API orchestration and side effects**.

---

## 1. Directory Structure

```text
execution/
├── gateway/         ⚡ Tool Gateway & Error Fix webhook endpoints
├── integrations/    🔌 Domain action-level leaf workflows
│   ├── google/      - calendar, gmail, drive, docs, sheets
│   ├── github/      - GitHub integrations
│   ├── media/       - Media services
│   ├── simple/      - news, gold, weather, search
│   ├── web/         - URL read, summarize, ask
│   └── shortlink/   - worker redirect & shortlinks
├── monitors/        🚨 Alerting & monitors
└── legacy/          ⏳ Legacy workflows being phased out
```

---

## 2. Gateway Workflows

All tool executions run through a single unified endpoint:

### Tool Gateway (`workflow_mia_tool_gateway.json`)
Receives execution requests from the Python Agent Core. It:
1. Validates the incoming token payload.
2. Extracts the `action` identifier (e.g., `calendar.create_event`, `web.read_url`, `github.get_release`).
3. Normalizes the structured args for the selected workflow, including web `fetchStrategy` and GitHub repo context for release / pull request / issue lookups.
4. Dispatches the parameters to the correct leaf integration workflow via an internal `Execute Workflow` node.
5. Gathers outputs, formats them into the stable `ok/text/result/links/meta` contract, and returns them to the Python Agent Core.

---

## 3. Workflow Sync Mechanism

Workflows are versioned inside git and synchronized to the web n8n instance using maintenance scripts:

### Single Workflow Sync
```bash
python scripts/maintenance/sync_workflows.py execution/gateway/workflow_mia_tool_gateway.json
```

### Auto Sync daemon
`scripts/sync/auto_sync.py` periodically scans files for changes and pushes them automatically to the API.

---

## 4. Design Guidelines for Workflows

When creating new integration workflows:
1. **Always return structured responses**: Ensure the final node outputs a JSON object containing the normalized contract fields (`ok`, `text`, `result`, `links`, `meta`).
2. **Keep logic thin**: Avoid putting complex decision loops or NLP parsing inside n8n. Let the Agent Core plan which workflow to trigger.
3. **Handle errors gracefully**: Put error boundary flags or catch nodes to return a meaningful error message to the gateway rather than raising an unhandled exception.
4. **Preserve token efficiency**: Keep visible link output capped and avoid duplicating text across `text`, `result`, and `meta` unless the data is needed downstream.
