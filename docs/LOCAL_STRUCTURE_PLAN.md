# Local Structure Plan

## Current Cleanup Direction

```text
n8n/
  docs/
  google/
  langchain_core/
  memory/
  scripts/
    workflow_patches/
  shortlink/
  workflow_*.json
```

## Intended Next Cleanup

### `docs/`

- architecture
- capability maps
- migration notes
- local structure notes

### `scripts/`

- `workflow_patches/`
- later:
  - `maintenance/`
  - `sync/`
  - `dev/`

### `workflow root`

Current root still contains:
- `workflow_mia_final_fix.json`
- `workflow_mia_tool_gateway.json`
- `workflow_sub_weather.json`
- `workflow_sub_gold.json`
- `workflow_sub_news.json`
- `workflow_sub_search.json`

Longer term direction:
- keep only top-level shared workflows at root
- move support workflows into clearer domain folders if references can be updated safely

## Constraint

Because many workflow filenames are already referenced in scripts, docs, and live synchronization flows, folder cleanup must happen gradually and safely rather than by a single destructive move.
