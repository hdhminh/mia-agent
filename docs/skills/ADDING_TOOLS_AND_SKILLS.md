# Adding Tools and Skills

## Add a tool

1. Define a LangChain tool under `agent/skills/` and map its Python name to one
   gateway action in `agent/skills/registry.py`.
2. Add or extend the corresponding workflow under `execution/integrations/` and
   route the action in `execution/gateway/workflow_mia_tool_gateway.json`.
3. If it changes external state, add the gateway action to
   `DANGEROUS_GATEWAY_NAMES`; approval and idempotency then apply automatically.
   Code-gateway tools (opencode) instead call `_run_code_guarded` in
   `agent/skills/code_runner/tools.py`, which creates a pending action for
   apply/publish/fix-issue-with-PR — the model cannot self-approve.
4. If it depends on a provider key or quota-bound API, document the required env
   vars and cost guardrails in `.env.example` plus deployment docs.
5. Regenerate the catalog:
   `python scripts/maintenance/generate_tool_catalog.py`.
6. Run `python scripts/maintenance/validate_tool_contracts.py` and
   `python scripts/maintenance/validate_workflow_json.py`.

`agent/tool_specs/catalog.yaml` is generated, not hand-edited. Its ToolSpec
records risk, approval, timeout, executor, workflow key, and discovery tags.

## Add a reusable skill

Add a record to `agent/skills_engine/skills.yaml` with a unique name, natural
language triggers, required capabilities, ordered steps, approval points, and
success criteria. Skill runs are persisted in `mia_skill_runs`, so completion
and failures are visible in operational metrics.

Keep steps outcome-oriented. A skill composes existing tools; it should not hide
an external write or weaken a tool's approval policy.

## MCP extension

Configure HTTPS servers through `MIA_MCP_SERVERS_JSON`. Only names listed under
`read_only_tools` are exposed by the adapter. Write-capable MCP tools require a
future policy and approval integration and are intentionally rejected today.
