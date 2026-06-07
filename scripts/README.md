# Scripts Layout

## Structure

```text
scripts/
  dev/
  maintenance/
  sync/
  workflow_patches/
```

- `dev/`: local helper scripts used during experiments or one-off data ingestion.
- `maintenance/`: operational helpers such as admin/error tooling.
- `sync/`: local sync and repository automation scripts.
- `workflow_patches/`: repo scripts that mutate workflow JSON definitions in place.

## Notes

- If a workflow JSON moves, update the corresponding script path here first.
- `workflow_patches/` should only contain scripts that patch checked-in workflow JSON files.
- Run `python3 scripts/maintenance/validate_repo_structure.py` after large cleanup or workflow patch batches.
- Run `python3 scripts/maintenance/smoke_safe_gateway.py` to verify safe direct/tool paths without creating, deleting, or sending real data.
- `workflow_patches/patch_action_id_guards_stage11.py` is a safety patch: it keeps Google read/search convenient, but requires exact IDs for high-risk write/delete/share actions.
