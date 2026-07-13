#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def load_constants(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0] if len(node.targets) == 1 else None
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = eval(compile(ast.Expression(node.value), str(path), "eval"), {"__builtins__": {}}, values)  # noqa: S307
        except Exception:
            continue
    return values


def main() -> int:
    registry = load_constants(ROOT / "agent/skills/registry.py")
    approvals = load_constants(ROOT / "agent/approval.py")
    mapping = registry["DIRECT_GATEWAY_TOOLS"]
    dangerous = set(approvals["DANGEROUS_GATEWAY_NAMES"])
    tools = []
    for name, action in sorted(mapping.items()):
        domain = action.split(".", 1)[0]
        risky = action in dangerous
        tools.append(
            {
                "name": name,
                "action": action,
                "domain": domain,
                "description": name.replace("_", " "),
                "risk": "external_write" if risky else "read",
                "approval": "always" if risky else "never",
                "idempotent": risky,
                "timeout_seconds": 60 if domain == "media" else 30,
                "executor": "n8n",
                "workflow_key": action,
                "tags": name.split("_"),
            }
        )
    code_tools = {
        "code_create_project": ("code.create_project", "Create a managed OpenCode project", "write", "never"),
        "code_import_existing_project": ("code.import_existing_project", "Import a local project into the OpenCode sandbox", "read", "never"),
        "code_work_on_project": ("code.work_on_project", "Continue coding inside a managed OpenCode project", "write", "never"),
        "code_project_status": ("code.project_status", "Show managed code project status", "read", "never"),
        "code_project_diff": ("code.project_diff", "Show managed code project diff", "read", "never"),
        "code_apply_to_existing_project": ("code.apply_to_existing_project", "Apply sandbox changes back to the imported local project", "external_write", "always"),
        "code_publish_project": ("code.publish_project", "Push a branch or create a pull request for a managed project", "external_write", "always"),
    }
    for name, (action, description, risk, approval) in code_tools.items():
        tools.append(
            {
                "name": name,
                "action": action,
                "domain": "code",
                "description": description,
                "risk": risk,
                "approval": approval,
                "idempotent": risk == "external_write",
                "timeout_seconds": 120,
                "executor": "opencode-gateway",
                "workflow_key": action,
                "tags": name.split("_"),
            }
        )
    target = ROOT / "agent/tool_specs/catalog.yaml"
    target.write_text(json.dumps({"version": 1, "tools": tools}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(tools)} ToolSpec entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
