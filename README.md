# n8n Workspace

This repository is being refactored toward a cleaner split:

- `n8n` for workflow runtime and integrations
- `mia-core` for routing/orchestration
- domain workflows grouped by capability

## Top-Level Layout

```text
n8n/
  docs/
  google/
  langchain_core/
  logs/
  memory/
  scripts/
  shortlink/
  workflows/
```

## Where To Look

- Architecture and migration notes:
  - [docs/README.md](/home/huynhminh/Projects/n8n/docs/README.md)
- Core workflow entrypoints:
  - [workflows/README.md](/home/huynhminh/Projects/n8n/workflows/README.md)
- Local helper scripts:
  - [scripts/README.md](/home/huynhminh/Projects/n8n/scripts/README.md)
- Google domain workflows:
  - [google/README.md](/home/huynhminh/Projects/n8n/google/README.md)

## Current Rule

The repo is being cleaned gradually and safely.

- Prefer updating paths and patch scripts together.
- Avoid moving domain workflow files again until their references are audited.
- Keep root focused on config and entrypoints, not piles of workflow JSON.
