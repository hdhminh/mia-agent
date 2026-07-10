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
    target = ROOT / "agent/tool_specs/catalog.yaml"
    target.write_text(json.dumps({"version": 1, "tools": tools}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"generated {len(tools)} ToolSpec entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
