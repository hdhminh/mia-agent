from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime

from agent.i18n import t
from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient


def _format_memory_search(rows: list[dict]) -> str:
    if not rows:
        return t("skills.memory_not_found", default="Mia không tìm thấy memory phù hợp.")

    lines = [t("skills.memory_matching_header", default="Memory phù hợp:")]
    for index, row in enumerate(rows, start=1):
        memory_type = row.get("memory_type", "general")
        title = str(row.get("title") or "").strip()
        prefix = f"{index}. [{memory_type}]"
        if title:
            prefix += f" {title}:"
        lines.append(f"{prefix} {row.get('chunk_text', '')}".strip())
    return "\n".join(lines)


def _format_memory_recent(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return t("skills.memory_recent_empty", default="Mia chưa có memory nào đáng chú ý gần đây.")

    lines = [t("skills.memory_recent_header", default="Memory gần đây:")]
    for index, row in enumerate(rows, start=1):
        memory_type = str(row.get("memory_type") or "general").strip()
        title = str(row.get("title") or "").strip()
        content = str(row.get("content") or row.get("chunk_text") or "").strip()
        snippet = content[:220].rstrip()
        if len(content) > 220:
            snippet += "..."
        prefix = f"{index}. [{memory_type}]"
        if title:
            prefix += f" {title}:"
        lines.append(f"{prefix} {snippet}".strip())
    return "\n".join(lines)


def _normalize_instruction(domain: str, action_label: str, instruction: str) -> str:
    text = " ".join(str(instruction or "").strip().split())
    return text or f"{domain} {action_label}"


def _has_structured_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _with_instruction_fallback(
    domain: str,
    action_label: str,
    payload: dict[str, Any],
    instruction: str = "",
    *structured_values: Any,
) -> dict[str, Any]:
    result = dict(payload)
    if any(_has_structured_value(value) for value in structured_values):
        return result
    cleaned_instruction = " ".join(str(instruction or "").strip().split())
    result["instruction"] = _normalize_instruction(domain, action_label, cleaned_instruction)
    return result


def _run_gateway_tool(
    tool_gateway: N8nToolGatewayClient,
    gateway_name: str,
    args: dict[str, Any],
    runtime: ToolRuntime[MiaContext],
) -> str:
    return tool_gateway.run_tool(gateway_name, args, runtime.context).text
