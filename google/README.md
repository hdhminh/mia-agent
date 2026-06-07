# Google Domain Workflows

This folder keeps the Google capability workflows grouped by domain:

- `gmail/`
- `calendar/`
- `drive/`
- `docs/`
- `sheets/`

## Why These Stay Here For Now

The repo is being cleaned gradually without breaking:

- local patch scripts
- workflow sync scripts
- docs links
- live workflow ID mapping in `workflows/core/workflow_mia_tool_gateway.json`

So the current rule is:

- keep Google workflows grouped by domain first
- only move them deeper into `workflows/google/...` after all path references are audited

## Current Migration Direction

The main architectural change is:

- `mia-core` decides capability + args
- `Mia Tool Gateway` maps capability to workflow
- each Google workflow should increasingly prefer `args` / `payload.args`
- leaf workflows should stop reparsing natural-language instructions wherever structured fields already exist

## Current Priority Domains

Most structured-args work has already landed in:

- `docs/`
- `drive/`
- `sheets/`
- `gmail/`
- `calendar/`

The remaining work is mostly:

- removing instruction-heavy fallbacks where safe
- normalizing outputs to the shared `ok/text/result/links/meta` shape
- cleaning side-effect-heavy actions carefully
