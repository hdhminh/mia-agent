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
    "README.md",
    "docker-compose.yml",
    "docs",
    "google",
    "langchain_core",
    "logs",
    "memory",
    "scripts",
    "shortlink",
    "workflows",
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
        if not name.startswith(".venv") and name not in {"tmp", "sync.log"}
    )
    if extra:
        errors.append("Unexpected root entries: " + ", ".join(extra))

    pycache_dirs = [
        path.relative_to(ROOT)
        for path in ROOT.rglob("__pycache__")
        if ".git" not in path.parts and not any(p.startswith(".venv") or p == "tmp" for p in path.parts)
    ]
    if pycache_dirs:
        errors.append(
            "Generated __pycache__ directories present: "
            + ", ".join(str(path) for path in pycache_dirs)
        )

    for path in list((ROOT / "google").rglob("*.json")) + list((ROOT / "workflows").rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - script should report any parse failure clearly.
            errors.append(f"Invalid JSON: {path.relative_to(ROOT)} ({exc})")

    for path in iter_text_files():
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in STALE_ROOT_REFERENCES:
            stale = f"/home/huynhminh/Projects/n8n/{name}"
            if stale in text:
                errors.append(f"Stale root path in {rel}: {stale}")
        if rel.parts[:2] == ("scripts", "workflow_patches") and "/home/huynhminh/Projects/n8n" in text:
            errors.append(f"Hard-coded repo path in workflow patch script: {rel}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("repo structure ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
