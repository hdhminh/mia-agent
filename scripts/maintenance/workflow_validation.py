#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


WORKFLOW_ID_RE = re.compile(r"^[A-Za-z0-9]{12,}$")
WORKFLOW_MAP_RE = re.compile(r"const\s+workflowMap\s*=\s*{(?P<body>[\s\S]*?)}\s*;", re.MULTILINE)
WORKFLOW_MAP_ENTRY_RE = re.compile(r"(?m)^\s*(?:'([^']+)'|([A-Za-z0-9_.-]+))\s*:\s*'([^']*)'\s*,?\s*$")


def _is_expression(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith("=") or "{{" in text or "}}" in text


def _is_workflow_id(value: str) -> bool:
    return bool(WORKFLOW_ID_RE.fullmatch(str(value or "").strip()))


def _nested_get(data: Any, path: list[Any]) -> Any:
    current = data
    for part in path:
        if isinstance(part, int):
            if not isinstance(current, list) or part < 0 or part >= len(current):
                return None
            current = current[part]
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _find_node(workflow: dict[str, Any], node_name: str) -> dict[str, Any] | None:
    nodes = workflow.get("nodes")
    if not isinstance(nodes, list):
        return None
    for node in nodes:
        if isinstance(node, dict) and str(node.get("name") or "").strip() == node_name:
            return node
    return None


def _validate_workflow_map(source: str, node_name: str, js_code: str) -> list[str]:
    issues: list[str] = []
    match = WORKFLOW_MAP_RE.search(js_code)
    if not match:
        issues.append(f"{source}: node '{node_name}' contains workflowMap but it could not be parsed.")
        return issues

    body = match.group("body") or ""
    entries: dict[str, str] = {}
    for line in body.splitlines():
        match_line = WORKFLOW_MAP_ENTRY_RE.match(line)
        if not match_line:
            continue
        key = match_line.group(1) or match_line.group(2) or ""
        value = match_line.group(3) or ""
        if key:
            entries[key] = value.strip()

    if not entries:
        issues.append(f"{source}: node '{node_name}' contains workflowMap but no entries were parsed.")
        return issues

    if "web.master" not in entries:
        issues.append(f"{source}: node '{node_name}' workflowMap is missing 'web.master'.")

    for key, value in entries.items():
        if not _is_workflow_id(value):
            issues.append(
                f"{source}: node '{node_name}' workflowMap['{key}'] = '{value}' does not look like a workflow ID."
            )

    return issues


def _validate_gateway_workflow(workflow: dict[str, Any], *, source: str) -> list[str]:
    issues: list[str] = []
    route_node = _find_node(workflow, "Route Tool")
    if route_node is None:
        issues.append(f"{source}: Mia: Tool Gateway is missing the 'Route Tool' node.")
        return issues

    params = route_node.get("parameters")
    if not isinstance(params, dict):
        issues.append(f"{source}: node 'Route Tool' parameters must be an object.")
        return issues

    js_code = params.get("jsCode")
    if not isinstance(js_code, str) or not js_code.strip():
        issues.append(f"{source}: node 'Route Tool' must contain jsCode.")
        return issues

    issues.extend(_validate_workflow_map(source, "Route Tool", js_code))
    return issues


def _validate_error_monitor_workflow(workflow: dict[str, Any], *, source: str) -> list[str]:
    issues: list[str] = []

    if_node = _find_node(workflow, "Co Gui Bao Loi?")
    if if_node is None:
        issues.append(f"{source}: Global Error Monitor is missing the 'Co Gui Bao Loi?' node.")
    else:
        if_expr = _nested_get(if_node, ["parameters", "conditions", "boolean", 0, "value1"])
        if_text = str(if_expr or "")
        required_cues = [
            "execution?.error?.context?.request?.body?.chat_id",
            "TELEGRAM_ADMIN_CHAT_ID",
        ]
        for cue in required_cues:
            if cue not in if_text:
                issues.append(
                    f"{source}: node 'Co Gui Bao Loi?' must keep fallback cue '{cue}' in the notify condition."
                )

    telegram_node = _find_node(workflow, "Gui Loi Telegram")
    if telegram_node is None:
        issues.append(f"{source}: Global Error Monitor is missing the 'Gui Loi Telegram' node.")
    else:
        chat_id_expr = _nested_get(telegram_node, ["parameters", "bodyParameters", "parameters", 0, "value"])
        chat_id_text = str(chat_id_expr or "")
        required_cues = [
            "execution?.error?.context?.request?.body?.chat_id",
            "TELEGRAM_ADMIN_CHAT_ID",
        ]
        for cue in required_cues:
            if cue not in chat_id_text:
                issues.append(
                    f"{source}: node 'Gui Loi Telegram' chat_id should keep fallback cue '{cue}'."
                )

    return issues


def validate_workflow_data(data: Any, *, source: str) -> list[str]:
    issues: list[str] = []
    if not isinstance(data, dict):
        return [f"{source}: workflow root must be a JSON object."]

    workflow_name = str(data.get("name") or "").strip()
    if not workflow_name:
        issues.append(f"{source}: workflow name is missing.")

    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        issues.append(f"{source}: workflow nodes must be a list.")
    else:
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                issues.append(f"{source}: node at index {index} must be an object.")
                continue

            node_name = str(node.get("name") or f"#{index}").strip()
            node_type = str(node.get("type") or "").strip()
            params = node.get("parameters")
            if not isinstance(params, dict):
                continue

            if node_type == "n8n-nodes-base.executeWorkflow":
                workflow_id = params.get("workflowId")
                if isinstance(workflow_id, str):
                    workflow_id = workflow_id.strip()
                    if workflow_id and not _is_expression(workflow_id) and not _is_workflow_id(workflow_id):
                        issues.append(
                            f"{source}: node '{node_name}' executeWorkflow.workflowId='{workflow_id}' does not look like a workflow ID."
                        )

    if isinstance(workflow_name, str):
        if workflow_name == "Mia: Tool Gateway" or source.endswith("workflow_mia_tool_gateway.json"):
            issues.extend(_validate_gateway_workflow(data, source=source))
        if workflow_name == "Global Error Monitor" or source.endswith("workflow_error_monitor.json"):
            issues.extend(_validate_error_monitor_workflow(data, source=source))

    return issues


def validate_workflow_file(path: Path | str) -> list[str]:
    workflow_path = Path(path)
    try:
        data = json.loads(workflow_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [f"{workflow_path}: file not found."]
    except json.JSONDecodeError as exc:
        return [f"{workflow_path}: invalid JSON: {exc}"]
    except Exception as exc:  # noqa: BLE001 - report parsing failure directly.
        return [f"{workflow_path}: unable to read workflow JSON: {exc}"]
    return validate_workflow_data(data, source=str(workflow_path))


def discover_default_workflow_files(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for rel in ("execution", "workflows", "google", "shortlink"):
        base = root / rel
        if base.exists():
            candidates.extend(sorted(base.rglob("*.json")))
    return candidates


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate n8n workflow JSON exports before sync.")
    parser.add_argument("paths", nargs="*", help="Workflow JSON files to validate. If omitted, scan known workflow directories.")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[2]
    paths = [Path(p) for p in args.paths] if args.paths else discover_default_workflow_files(root)

    if not paths:
        print("No workflow JSON files found.", file=sys.stderr)
        return 1

    exit_code = 0
    for path in paths:
        issues = validate_workflow_file(path)
        if issues:
            exit_code = 1
            print(f"INVALID {path}", file=sys.stderr)
            for issue in issues:
                print(f"  - {issue}", file=sys.stderr)
        else:
            print(f"OK {path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
