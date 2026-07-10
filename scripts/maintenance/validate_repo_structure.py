#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ROOT = {
    ".env",
    ".env.example",
    ".git",
    ".gitignore",
    ".github",
    "LICENSE",
    "README.md",
    "SHOWCASE.md",
    "requirements.txt",
    "requirements-dev.txt",
    "pyproject.toml",
    "docs",
    "agent",
    "execution",
    "infra",
    "scripts",
    "tests",
    "logs",
}

STALE_ROOT_REFERENCES = (
    "workflow_mia_final_fix.json",
    "workflow_mia_tool_gateway.json",
    "workflow_sub_weather.json",
    "workflow_sub_gold.json",
    "workflow_sub_news.json",
    "workflow_sub_search.json",
    "chatbot_current.json",
    "auto_sync.py",
    "auto_error_workflow.py",
    "ingest.py",
    "ingest.js",
)

TEXT_SUFFIXES = {".md", ".py", ".js", ".json", ".txt", ".yml", ".yaml"}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or any(p.startswith(".venv") or p == "tmp" for p in path.parts):
            continue
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            files.append(path)
    return files


def main() -> int:
    errors: list[str] = []

    root_names = {path.name for path in ROOT.iterdir()}
    extra = sorted(
        name for name in root_names - ALLOWED_ROOT
        if not name.startswith(".venv") and name not in {"tmp", "sync.log", ".pytest_cache", ".ruff_cache"}
    )
    if extra:
        errors.append("Unexpected root entries: " + ", ".join(extra))



    for path in list((ROOT / "execution").rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - script should report any parse failure clearly.
            errors.append(f"Invalid JSON: {path.relative_to(ROOT)} ({exc})")

    import re
    for path in iter_text_files():
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in STALE_ROOT_REFERENCES:
            for root_name in ("n8n", "mia-agent"):
                pattern = rf"/home/[^/]+/Projects/{root_name}/{name}"
                if re.search(pattern, text):
                    errors.append(f"Stale root path in {rel}")
        if rel.parts[:2] == ("scripts", "patches"):
            if re.search(r"/home/[^/]+/Projects/(n8n|mia-agent)", text):
                errors.append(f"Hard-coded repo path in workflow patch script: {rel}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("repo structure ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
