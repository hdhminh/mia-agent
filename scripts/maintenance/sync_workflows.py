#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ALLOWED_SETTINGS_KEYS = {
    "saveExecutionProgress",
    "saveManualExecutions",
    "saveDataErrorExecution",
    "saveDataSuccessExecution",
    "executionTimeout",
    "timezone",
    "errorWorkflow",
    "executionOrder",
}

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from workflow_validation import validate_workflow_data  # noqa: E402


def load_env_file(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


class N8nApi:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {
            "Accept": "application/json",
            "X-N8N-API-KEY": self.api_key,
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            headers=headers,
            data=data,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {method} {self.base_url}{path}\n{detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot connect to {self.base_url}{path}\n{exc}") from exc

    def list_workflows(self) -> list[dict[str, Any]]:
        data = self.request("GET", "/api/v1/workflows?limit=250")
        return data.get("data", []) if isinstance(data, dict) else []

    def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self.request("GET", f"/api/v1/workflows/{workflow_id}")

    def update_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PUT", f"/api/v1/workflows/{workflow_id}", payload)

    def create_workflow(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/api/v1/workflows", payload)

    def activate_workflow(self, workflow_id: str) -> dict[str, Any]:
        return self.request("POST", f"/api/v1/workflows/{workflow_id}/activate")


def build_payload(local: dict[str, Any], remote: dict[str, Any]) -> dict[str, Any]:
    remote_settings = dict(remote.get("settings") or {})
    local_settings = dict(local.get("settings") or {})

    settings = {
        key: value
        for key, value in {**remote_settings, **local_settings}.items()
        if key in ALLOWED_SETTINGS_KEYS
    }

    payload: dict[str, Any] = {
        "name": local.get("name") or remote.get("name"),
        "nodes": local.get("nodes", []),
        "connections": local.get("connections", {}),
        "settings": settings,
    }

    if "pinData" in local or "pinData" in remote:
        payload["pinData"] = local.get("pinData") or {}

    if "staticData" in remote:
        payload["staticData"] = remote.get("staticData")

    return payload


def canonical_subset(data: dict[str, Any]) -> str:
    subset = {
        "name": data.get("name"),
        "nodes": data.get("nodes", []),
        "connections": data.get("connections", {}),
        "settings": {
            key: value
            for key, value in dict(data.get("settings") or {}).items()
            if key in ALLOWED_SETTINGS_KEYS
        },
        "pinData": data.get("pinData") or {},
    }
    return json.dumps(subset, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_workflow_spec(spec: str) -> tuple[str | None, str | None, Path]:
    parts = spec.split("::")
    if len(parts) == 3:
        workflow_id, workflow_name, raw_path = parts
        return workflow_id.strip() or None, workflow_name.strip() or None, Path(raw_path)
    if len(parts) == 2:
        first, raw_path = parts
        first = first.strip()
        workflow_id = first if len(first) >= 12 and " " not in first else None
        workflow_name = None if workflow_id else first
        return workflow_id, workflow_name, Path(raw_path)
    return None, None, Path(spec)


def main() -> int:
    load_env_file(".env")

    parser = argparse.ArgumentParser(description="Sync local n8n workflow JSON files to the running n8n instance.")
    parser.add_argument("paths", nargs="+", help="Workflow JSON paths to sync.")
    parser.add_argument("--base-url", default=os.getenv("N8N_BASE_URL", "http://localhost:5678"))
    parser.add_argument("--api-key", default=os.getenv("N8N_API_KEY", ""))
    parser.add_argument("--create-missing", action="store_true", help="Create workflows that do not already exist on n8n.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.api_key:
        print("Missing N8N_API_KEY", file=sys.stderr)
        return 2

    api = N8nApi(args.base_url, args.api_key)
    workflows = api.list_workflows()
    by_name = {str(wf.get("name") or "").strip(): wf for wf in workflows}
    by_id = {str(wf.get("id") or "").strip(): wf for wf in workflows}

    exit_code = 0
    for spec in args.paths:
        explicit_id, explicit_name, path = parse_workflow_spec(spec)
        if not path.exists():
            print(f"SKIP {path}: file not found", file=sys.stderr)
            exit_code = 1
            continue

        local = json.loads(path.read_text(encoding="utf-8"))
        issues = validate_workflow_data(local, source=str(path))
        if issues:
            print(f"SKIP {path}: workflow validation failed", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
            exit_code = 1
            continue

        name = explicit_name or str(local.get("name") or "").strip()
        if not name and not explicit_id:
            print(f"SKIP {path}: workflow name missing", file=sys.stderr)
            exit_code = 1
            continue

        remote_stub = by_id.get(explicit_id or "") if explicit_id else by_name.get(name)
        if not remote_stub:
            if args.create_missing:
                payload = build_payload(local, {})
                if args.dry_run:
                    print(f"DRY-RUN CREATE {name}")
                    continue
                created = api.create_workflow(payload)
                created_id = str(created.get("id") or "").strip()
                if created_id:
                    api.activate_workflow(created_id)
                print(f"CREATED {name} ({created_id or 'unknown-id'})")
                continue
            target = f"id '{explicit_id}'" if explicit_id else f"name '{name}'"
            print(f"SKIP {path}: remote workflow not found for {target}", file=sys.stderr)
            exit_code = 1
            continue

        remote = api.get_workflow(str(remote_stub["id"]))
        payload = build_payload(local, remote)
        if canonical_subset(payload) == canonical_subset(remote):
            print(f"UNCHANGED {name} ({remote_stub['id']})")
            continue

        if args.dry_run:
            print(f"DRY-RUN {name} ({remote_stub['id']})")
            continue

        api.update_workflow(str(remote_stub["id"]), payload)
        print(f"UPDATED {name} ({remote_stub['id']})")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
