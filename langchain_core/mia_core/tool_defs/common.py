from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime

from mia_core.models import MiaContext
from mia_core.n8n_client import N8nToolGatewayClient


def _format_memory_search(rows: list[dict]) -> str:
    if not rows:
        return "Mia không tìm thấy memory phù hợp."

    lines = ["Memory phù hợp:"]
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
        return "Mia chưa có memory nào đáng chú ý gần đây."

    lines = ["Memory gần đây:"]
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


def _run_gateway_tool(
    tool_gateway: N8nToolGatewayClient,
    gateway_name: str,
    args: dict[str, Any],
    runtime: ToolRuntime[MiaContext],
) -> str:
    return tool_gateway.run_tool(gateway_name, args, runtime.context).text
