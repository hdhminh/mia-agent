#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _load_registry_constants() -> dict[str, Any]:
    source = (ROOT / "agent/skills/registry.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        target = node.target if isinstance(node, ast.AnnAssign) else node.targets[0] if len(node.targets) == 1 else None
        if not isinstance(target, ast.Name):
            continue
        try:
            values[target.id] = eval(  # noqa: S307 - evaluated AST is repository-owned constant data
                compile(ast.Expression(node.value), "registry.py", "eval"),
                {"__builtins__": {}},
                values,
            )
        except Exception:
            continue
    return values


def _gateway_actions() -> set[str]:
    workflow = json.loads((ROOT / "execution/gateway/workflow_mia_tool_gateway.json").read_text(encoding="utf-8"))
    node = next(item for item in workflow["nodes"] if item.get("name") == "Prepare Tool Request")
    code = str(node.get("parameters", {}).get("jsCode") or "")
    return set(re.findall(r"^\s*'([^']+)'\s*:\s*\{", code, flags=re.MULTILINE))


def main() -> int:
    constants = _load_registry_constants()
    mapping = constants.get("DIRECT_GATEWAY_TOOLS") or {}
    if not isinstance(mapping, dict) or not mapping:
        print("DIRECT_GATEWAY_TOOLS could not be loaded.", file=sys.stderr)
        return 1
    expected = set(str(value) for value in mapping.values())
    actual = _gateway_actions()
    catalog_payload = json.loads((ROOT / "agent/tool_specs/catalog.yaml").read_text(encoding="utf-8"))
    catalog_rows = catalog_payload.get("tools", []) if isinstance(catalog_payload, dict) else []
    catalog_mapping = {
        str(row.get("name") or ""): str(row.get("action") or "")
        for row in catalog_rows
        if isinstance(row, dict) and row.get("name") and row.get("action")
    }
    missing = sorted(expected - actual)
    if missing:
        print("Gateway actions missing for registered tools:", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)
        return 1
    if mapping != catalog_mapping:
        missing_specs = sorted(set(mapping) - set(catalog_mapping))
        stale_specs = sorted(set(catalog_mapping) - set(mapping))
        mismatched = sorted(name for name in set(mapping) & set(catalog_mapping) if mapping[name] != catalog_mapping[name])
        print(
            f"ToolSpec drift: missing={missing_specs}, stale={stale_specs}, mismatched={mismatched}",
            file=sys.stderr,
        )
        return 1
    print(f"tool contracts ok: {len(mapping)} Python tools, {len(actual)} gateway actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
