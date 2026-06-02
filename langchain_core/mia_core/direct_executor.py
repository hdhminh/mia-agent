from __future__ import annotations

from dataclasses import dataclass

from mia_core.capabilities import DIRECT_GATEWAY_TOOLS, DIRECT_ROUTE_TOOLS
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
from mia_core.request_parser import build_direct_tool_args, should_allow_direct_route
from mia_core.response_normalizer import sanitize_final_text


def build_memory_recent_text(memory_repo: MemoryRepository, chat_id: str, limit: int = 5) -> str:
    rows = memory_repo.recent(chat_id=chat_id, limit=max(1, min(limit, 10)))
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


@dataclass
class DirectExecutor:
    memory_repo: MemoryRepository
    tool_gateway: N8nToolGatewayClient

    def execute(
        self,
        request: MiaChatRequest,
        context: MiaContext,
        hint_tool: str,
        *,
        allow_multistep: bool = False,
    ) -> MiaChatResponse | None:
        if not hint_tool or hint_tool not in DIRECT_ROUTE_TOOLS:
            return None
        if not allow_multistep and not should_allow_direct_route(hint_tool, request.text):
            return None

        request_id = context.request_id
        thread_id = request.resolved_thread_id()

        if hint_tool == "memory_recent":
            text = build_memory_recent_text(self.memory_repo, request.chat_id)
            return MiaChatResponse(
                final_text=sanitize_final_text(text),
                tools_called=["memory_recent"],
                thread_id=thread_id,
                request_id=request_id,
            )

        gateway_name = DIRECT_GATEWAY_TOOLS.get(hint_tool)
        if not gateway_name:
            return None

        args = build_direct_tool_args(hint_tool, request.text)
        try:
            result = self.tool_gateway.run_tool(
                gateway_name,
                args,
                context,
                request_text=request.text,
            )
        except Exception:
            return None

        final_text = sanitize_final_text(result.text)
        if not final_text:
            return None

        return MiaChatResponse(
            final_text=final_text,
            tools_called=[hint_tool],
            thread_id=thread_id,
            request_id=request_id,
        )
