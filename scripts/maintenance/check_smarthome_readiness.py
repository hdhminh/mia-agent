#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = ROOT / ".env"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def clean(value: Any) -> str:
    return str(value or "").strip()


def check_tcp(host: str, port: int, timeout: float = 2.0) -> tuple[bool, str]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
    except OSError as exc:
        return False, str(exc)
    finally:
        sock.close()
    return True, "ok"


def http_status(url: str, token: str = "", timeout: float = 5.0) -> tuple[bool, int | None, str]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url=url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return True, response.status, "ok"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        return False, exc.code, detail or exc.reason
    except urllib.error.URLError as exc:
        return False, None, str(exc)


def run_command(args: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return False, str(exc)
    output = completed.stdout.strip() or completed.stderr.strip()
    return completed.returncode == 0, output


def docker_status_map() -> dict[str, str]:
    ok, output = run_command(
        [
            "docker",
            "ps",
            "--format",
            "{{.Names}}\t{{.Status}}",
        ]
    )
    if not ok:
        return {}
    rows: dict[str, str] = {}
    for line in output.splitlines():
        if "\t" not in line:
            continue
        name, status = line.split("\t", 1)
        rows[clean(name)] = clean(status)
    return rows


def http_status_from_n8n(url: str, token: str = "") -> tuple[bool, str]:
    headers_json = json.dumps(
        {"Accept": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
        ensure_ascii=False,
    )
    script = textwrap.dedent(
        f"""
        const http = require('http');
        const https = require('https');
        const target = {json.dumps(url)};
        const headers = {headers_json};
        const client = target.startsWith('https://') ? https : http;
        const req = client.request(target, {{ method: 'GET', headers }}, (res) => {{
          process.stdout.write(String(res.statusCode || ''));
          res.resume();
        }});
        req.on('error', (err) => {{
          process.stderr.write(String(err.message || err));
          process.exit(2);
        }});
        req.end();
        """
    ).strip()
    ok, output = run_command(["docker", "exec", "n8n", "node", "-e", script])
    if not output:
        return ok, "no output"
    if ok and output.isdigit():
        return output in {"200", "401", "403"}, f"status={output}"
    return False, output


def workflow_present(name: str) -> tuple[bool, str]:
    api_key = clean(os.getenv("N8N_API_KEY"))
    if not api_key:
        return False, "missing N8N_API_KEY"
    base_url = clean(os.getenv("N8N_BASE_URL") or "http://127.0.0.1:5678").rstrip("/")
    req = urllib.request.Request(
        url=f"{base_url}/api/v1/workflows?limit=250",
        method="GET",
        headers={"Accept": "application/json", "X-N8N-API-KEY": api_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except Exception as exc:  # broad on purpose for readiness reporting
        return False, str(exc)
    for item in payload.get("data", []) if isinstance(payload, dict) else []:
        if clean(item.get("name")) == name:
            return True, clean(item.get("id")) or "found"
    return False, "not found"


def main() -> int:
    load_env_file(ENV_PATH)

    report: list[tuple[str, bool, str]] = []

    dashboard_url = clean(os.getenv("MIA_HOME_DASHBOARD_URL") or "http://127.0.0.1:8123")
    ha_url = clean(os.getenv("HOME_ASSISTANT_URL") or "http://host.docker.internal:8123")
    ha_token = clean(os.getenv("HOME_ASSISTANT_TOKEN"))
    default_area = clean(os.getenv("MIA_HOME_DEFAULT_AREA"))
    allowed_label = clean(os.getenv("MIA_HOME_ALLOWED_LABEL") or "mia_allowed")
    aliases_json = clean(os.getenv("MIA_HOME_ENTITY_ALIASES_JSON"))

    containers = docker_status_map()
    for service_name in ("home-assistant", "n8n", "mia-core", "memory-embedder"):
        status = containers.get(service_name, "not running")
        report.append((f"container:{service_name}", service_name in containers, status))

    ok, detail = check_tcp("127.0.0.1", 8123)
    report.append(("tcp:home_assistant_8123", ok, detail))

    ok, detail = check_tcp("127.0.0.1", 8000)
    report.append(("tcp:mia_core_8000", ok, detail))

    ok, detail = check_tcp("127.0.0.1", 5678)
    report.append(("tcp:n8n_5678", ok, detail))

    dashboard_ok, dashboard_status, dashboard_detail = http_status(dashboard_url)
    report.append(
        (
            "http:dashboard",
            dashboard_ok or dashboard_status in {200, 401, 403, 405},
            f"status={dashboard_status} detail={dashboard_detail}",
        )
    )

    ha_api_ok, ha_api_status, ha_api_detail = http_status(f"{ha_url.rstrip('/')}/api/", ha_token)
    report.append(
        (
            "http:home_assistant_api",
            ha_api_ok or ha_api_status in {200, 401, 403},
            f"status={ha_api_status} detail={ha_api_detail}",
        )
    )

    if "n8n" in containers:
        ok, detail = http_status_from_n8n(f"{ha_url.rstrip('/')}/api/", ha_token)
        report.append(("http:home_assistant_api_from_n8n", ok, detail))

    report.append(("env:home_assistant_token", bool(ha_token), "set" if ha_token else "missing"))
    report.append(("env:default_area", bool(default_area), default_area or "missing"))
    report.append(("env:allowed_label", bool(allowed_label), allowed_label or "missing"))

    if aliases_json:
        try:
            alias_payload = json.loads(aliases_json)
            alias_count = len(alias_payload) if isinstance(alias_payload, dict) else 0
            report.append(("env:aliases_json", isinstance(alias_payload, dict), f"{alias_count} aliases"))
        except json.JSONDecodeError as exc:
            report.append(("env:aliases_json", False, f"invalid json: {exc}"))
    else:
        report.append(("env:aliases_json", False, "missing"))

    for workflow_name in (
        "Mia: Tool Gateway",
        "Sub-workflow: Home Assistant Smart Home Master",
    ):
        ok, detail = workflow_present(workflow_name)
        report.append((f"workflow:{workflow_name}", ok, detail))

    print("Smart-home readiness report")
    print(f"- repo: {ROOT}")
    print(f"- dashboard_url: {dashboard_url}")
    print(f"- home_assistant_url_for_n8n: {ha_url}")
    print("")

    failing = 0
    for label, ok, detail in report:
        marker = "OK" if ok else "WARN"
        print(f"[{marker}] {label}: {detail}")
        if not ok:
            failing += 1

    print("")
    print("Suggested next actions:")
    if not ha_token:
        print("- Create a Home Assistant Long-Lived Access Token and set HOME_ASSISTANT_TOKEN in .env.")
    if not aliases_json:
        print("- Run `python scripts/maintenance/bootstrap_home_assistant_inventory.py --format env` after token setup.")
    if not default_area:
        print("- Set MIA_HOME_DEFAULT_AREA to the main room, for example `Phòng ngủ`.")
    if failing == 0:
        print("- Smart-home stack looks ready for device labeling and command testing.")

    return 0 if failing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
