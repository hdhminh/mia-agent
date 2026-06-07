# Workflows Layout

## Purpose

This folder groups local workflow JSON files by runtime role so the repo root stays focused on code and environment files.

## Structure

```text
workflows/
  core/
  simple/
  legacy/
```

- `core/`: primary entrypoints and global operational workflows.
- `simple/`: small direct helper workflows used by Mia for deterministic capabilities.
- `legacy/`: old or compatibility workflows kept locally for reference only.

## Notes

- Google domain workflows stay under `google/` because they already form clear domain packages.
- Memory workflows stay under `memory/`.
- Shortlink workflows stay under `shortlink/`.
- If a script patches a workflow JSON directly, update that script when moving files.
