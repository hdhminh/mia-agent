#!/usr/bin/env python3
import os
import sys
import json
import argparse
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional



DEFAULT_ERROR_WORKFLOW_NAME = "Global Error Monitor"


class N8nApi:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"

        headers = {
            "Accept": "application/json",
            "X-N8N-API-KEY": self.api_key,
        }

        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url=url,
            data=data,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {e.code} {method} {url}\n{detail}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Cannot connect to n8n API: {url}\n{e}") from e

    def list_workflows(self) -> List[Dict[str, Any]]:
        workflows: List[Dict[str, Any]] = []
        cursor = None

        while True:
            path = "/api/v1/workflows?limit=100"
            if cursor:
                path += f"&cursor={cursor}"

            data = self.request("GET", path)
            batch = data.get("data", data if isinstance(data, list) else [])
            workflows.extend(batch)

            cursor = data.get("nextCursor") if isinstance(data, dict) else None
            if not cursor:
                break

        return workflows

    def get_workflow(self, workflow_id: str) -> Dict[str, Any]:
        return self.request("GET", f"/api/v1/workflows/{workflow_id}")

    def update_workflow(self, workflow_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.request("PUT", f"/api/v1/workflows/{workflow_id}", payload)


def load_env_file(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            os.environ.setdefault(key, value)


def find_error_workflow(
    workflows: List[Dict[str, Any]],
    error_workflow_id: Optional[str],
    error_workflow_name: str,
) -> Dict[str, Any]:
    if error_workflow_id:
        for wf in workflows:
            if str(wf.get("id")) == str(error_workflow_id):
                return wf

        raise RuntimeError(f"Không tìm thấy error workflow id: {error_workflow_id}")

    matches = [
        wf for wf in workflows
        if str(wf.get("name") or "").strip() == error_workflow_name
    ]

    if not matches:
        sample = "\n".join(
            f"- {wf.get('name')} ({wf.get('id')})"
            for wf in workflows[:30]
        )

        raise RuntimeError(
            f"Không tìm thấy error workflow tên: {error_workflow_name}\n\n"
            f"Workflow hiện có:\n{sample}"
        )

    if len(matches) > 1:
        found = "\n".join(
            f"- {wf.get('name')} ({wf.get('id')})"
            for wf in matches
        )

        raise RuntimeError(
            f"Có nhiều workflow cùng tên {error_workflow_name}. "
            f"Hãy dùng --error-workflow-id.\n{found}"
        )

    return matches[0]


def should_skip_workflow(
    wf: Dict[str, Any],
    error_workflow_id: str,
    include_inactive: bool,
    skip_name_contains: List[str],
) -> Optional[str]:
    wf_id = str(wf.get("id") or "")
    name = str(wf.get("name") or "")

    if wf_id == str(error_workflow_id):
        return "bỏ qua chính Global Error Monitor"

    if not include_inactive and not wf.get("active", False):
        return "bỏ qua workflow inactive"

    lowered = name.lower()
    for part in skip_name_contains:
        if part.lower() in lowered:
            return f"bỏ qua theo filter tên: {part}"

    return None


def build_update_payload(full: Dict[str, Any], error_workflow_id: str) -> Dict[str, Any]:
    """
    n8n API validates workflow.settings strictly.
    Do not send unknown settings fields back, otherwise API returns:
    "request/body/settings must NOT have additional properties"
    """

    original_settings = dict(full.get("settings") or {})

    allowed_settings_keys = {
        "saveExecutionProgress",
        "saveManualExecutions",
        "saveDataErrorExecution",
        "saveDataSuccessExecution",
        "executionTimeout",
        "timezone",
        "errorWorkflow",
        "executionOrder",
    }

    settings = {
        key: value
        for key, value in original_settings.items()
        if key in allowed_settings_keys
    }

    settings["errorWorkflow"] = str(error_workflow_id)

    payload: Dict[str, Any] = {
        "name": full.get("name"),
        "nodes": full.get("nodes", []),
        "connections": full.get("connections", {}),
        "settings": settings,
    }

    if "pinData" in full:
        payload["pinData"] = full.get("pinData") or {}

    if "staticData" in full:
        payload["staticData"] = full.get("staticData")

    return payload


def main() -> int:
    load_env_file(".env")

    parser = argparse.ArgumentParser(
        description="Auto set Global Error Monitor as n8n Error Workflow."
    )

    parser.add_argument(
        "--base-url",
        default=os.getenv("N8N_BASE_URL", "http://localhost:5678"),
        help="n8n base URL. Default: N8N_BASE_URL or http://localhost:5678",
    )

    parser.add_argument(
        "--api-key",
        default=os.getenv("N8N_API_KEY", ""),
        help="n8n API key. Default: N8N_API_KEY from env/.env",
    )

    parser.add_argument(
        "--error-workflow-name",
        default=os.getenv("N8N_ERROR_WORKFLOW_NAME", DEFAULT_ERROR_WORKFLOW_NAME),
        help=f"Error workflow name. Default: {DEFAULT_ERROR_WORKFLOW_NAME}",
    )

    parser.add_argument(
        "--error-workflow-id",
        default=os.getenv("N8N_ERROR_WORKFLOW_ID", ""),
        help="Error workflow id. Overrides name lookup.",
    )

    parser.add_argument(
        "--include-inactive",
        action="store_true",
        help="Update inactive workflows too. Default: active only.",
    )

    parser.add_argument(
        "--skip-name-contains",
        action="append",
        default=[],
        help="Skip workflows whose name contains this text. Can be repeated.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without updating.",
    )

    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: Thiếu N8N_API_KEY trong .env hoặc env.", file=sys.stderr)
        print("Thêm vào .env ví dụ:", file=sys.stderr)
        print("N8N_API_KEY=your_api_key_here", file=sys.stderr)
        return 2

    api = N8nApi(args.base_url, args.api_key)

    print(f"[INFO] n8n base URL: {args.base_url}")
    print("[INFO] Đang lấy danh sách workflow...")

    workflows = api.list_workflows()
    print(f"[INFO] Tìm thấy {len(workflows)} workflow")

    error_wf = find_error_workflow(
        workflows=workflows,
        error_workflow_id=args.error_workflow_id or None,
        error_workflow_name=args.error_workflow_name,
    )

    error_workflow_id = str(error_wf.get("id"))
    print(f"[INFO] Error workflow: {error_wf.get('name')} ({error_workflow_id})")

    planned = []
    skipped = []

    for wf in workflows:
        reason = should_skip_workflow(
            wf=wf,
            error_workflow_id=error_workflow_id,
            include_inactive=args.include_inactive,
            skip_name_contains=args.skip_name_contains,
        )

        if reason:
            skipped.append((wf, reason))
            continue

        wf_id = str(wf.get("id"))
        full = api.get_workflow(wf_id)

        current_error_wf = str(
            (full.get("settings") or {}).get("errorWorkflow") or ""
        )

        if current_error_wf == error_workflow_id:
            skipped.append((wf, "đã gắn rồi"))
            continue

        planned.append((wf, full, current_error_wf))

    print(f"[INFO] Sẽ cập nhật: {len(planned)} workflow")
    print(f"[INFO] Bỏ qua: {len(skipped)} workflow")

    for wf, _full, current in planned:
        print(
            f"[PLAN] {wf.get('name')} ({wf.get('id')}) "
            f"errorWorkflow: {current or '-'} -> {error_workflow_id}"
        )

    if args.dry_run:
        print("[DRY RUN] Không cập nhật workflow nào.")
        return 0

    updated = 0
    failed = 0

    for wf, full, _current in planned:
        wf_id = str(wf.get("id"))
        name = wf.get("name")
        payload = build_update_payload(full, error_workflow_id)

        try:
            api.update_workflow(wf_id, payload)
            updated += 1
            print(f"[OK] Đã cập nhật: {name} ({wf_id})")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {name} ({wf_id})\n{e}", file=sys.stderr)

    print("")
    print("Xong.")
    print(f"Đã cập nhật: {updated}")
    print(f"Lỗi: {failed}")
    print(f"Bỏ qua: {len(skipped)}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())