#!/usr/bin/env bash
# Hourly validation of all exported n8n workflow files.
# Intentionally dry-run: validates JSON + tool contracts and reports diffs,
# never commits or pushes (auto_sync.py refuses the default branch anyway).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${PYTHON:-python3}"

# All exported workflows (git-tracked).
mapfile -t WORKFLOWS < <(git -C "$ROOT" ls-files 'execution/**/workflow_*.json' 'execution/gateway/*.json' | sort)

if [ "${#WORKFLOWS[@]}" -eq 0 ]; then
  echo "No workflow files found to sync." >&2
  exit 1
fi

exec "$PY" "$ROOT/scripts/sync/auto_sync.py" "${WORKFLOWS[@]}"
