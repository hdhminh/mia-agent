# Local Structure Plan

## Current Cleanup Direction

```text
n8n/
  docs/
  google/
  langchain_core/
  logs/
  memory/
  scripts/
    dev/
    maintenance/
    sync/
    workflow_patches/
  shortlink/
  workflows/
    core/
    simple/
    legacy/
```

## Intended Next Cleanup

### `docs/`

- architecture
- capability maps
- migration notes
- local structure notes

### `google/`

- domain folders kept separate for now:
  - `gmail/`
  - `calendar/`
  - `drive/`
  - `docs/`
  - `sheets/`
- do not move these deeper until all patch/sync references are audited

### `scripts/`

Current grouped layout:
- `scripts/dev/`
- `scripts/maintenance/`
- `scripts/sync/`
- `scripts/workflow_patches/`

### `workflows/`

Current grouped layout:
- `workflows/core/`
  - `workflow_mia_final_fix.json`
  - `workflow_mia_tool_gateway.json`
  - `workflow_error_monitor.json`
- `workflows/simple/`
  - `workflow_sub_weather.json`
  - `workflow_sub_gold.json`
  - `workflow_sub_news.json`
  - `workflow_sub_search.json`
- `workflows/legacy/`
  - `chatbot_current.json`

Next cleanup direction:
- keep root almost code/config-only
- group workflow JSON by runtime role first
- keep domain-specific Google workflow files under `google/` until structured-args migration is stable
- only move more files when path references are audited

## What Has Already Been Cleaned

- root now keeps mostly:
  - `.env`, `.env.example`, `.gitignore`, `docker-compose.yml`
- docs have been moved under `docs/`
- primary workflow entrypoints live under `workflows/`
- local automation scripts are grouped under `scripts/`
- runtime logs are grouped under `logs/`
- stray root `sync.log` should not be recreated; keep sync output under `logs/sync.log`
- Google domain workflow JSON files stay grouped under `google/`
- memory workflows stay under `memory/`
- shortlink workflows stay under `shortlink/`

## Remaining Safe Cleanup

- keep deleting generated `__pycache__/` folders from the repo tree
- add small README files where folder purpose is not obvious
- continue documenting path decisions before doing deeper moves
- run `python3 scripts/maintenance/validate_repo_structure.py` before considering cleanup complete
- run `python3 scripts/maintenance/smoke_safe_gateway.py` after workflow gateway/core changes to check safe paths without destructive side effects

## Cleanup Deferred On Purpose

- moving `google/*` into `workflows/google/*`
- moving `memory/*` and `shortlink/*` again
- renaming workflow JSON files at scale

These are intentionally deferred until the patch scripts, docs links, and live sync assumptions are fully audited.

## Constraint

Because many workflow filenames are already referenced in scripts, docs, and live synchronization flows, deeper cleanup still has to happen gradually and safely rather than by a single destructive move.
