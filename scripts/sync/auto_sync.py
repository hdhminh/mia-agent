#!/usr/bin/env python3
"""Validate and optionally commit selected workflow files.

This command is deliberately dry-run by default. It never pulls, rebases, or
pushes, and it refuses to create commits on the default branch.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=capture)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="Explicit repository-relative files to validate/stage.")
    parser.add_argument("--commit", action="store_true", help="Commit only the selected paths after validation.")
    parser.add_argument("--message", default="Update n8n workflows", help="Commit message used with --commit.")
    return parser.parse_args()


def resolve_paths(values: list[str]) -> list[str]:
    resolved: list[str] = []
    for value in values:
        candidate = (ROOT / value).resolve()
        if ROOT not in candidate.parents or not candidate.is_file():
            raise ValueError(f"Path must be an existing file inside the repository: {value}")
        resolved.append(str(candidate.relative_to(ROOT)))
    return resolved


def main() -> int:
    args = parse_args()
    try:
        paths = resolve_paths(args.paths)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    run([sys.executable, "scripts/maintenance/validate_workflow_json.py"])
    run([sys.executable, "scripts/maintenance/validate_tool_contracts.py"])
    diff = run(["git", "diff", "--", *paths], capture=True).stdout
    if not diff.strip():
        print("Selected files have no unstaged changes.")
        return 0

    print(diff)
    if not args.commit:
        print("Dry run only. Re-run with --commit to stage and commit these exact files.")
        return 0

    branch = run(["git", "branch", "--show-current"], capture=True).stdout.strip()
    if branch in {"main", "master"}:
        print("Refusing to commit on the default branch. Create a feature branch first.", file=sys.stderr)
        return 2
    run(["git", "add", "--", *paths])
    run(["git", "commit", "-m", args.message, "--", *paths])
    print(f"Committed {len(paths)} selected file(s) on {branch}. Push remains an explicit operator action.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
