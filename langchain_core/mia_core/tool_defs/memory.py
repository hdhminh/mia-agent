from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime, tool

from mia_core.models import MiaContext
from mia_core.memory import MemoryRepository
from mia_core.tool_defs.common import _format_memory_search, _format_memory_recent


def get_memory_tools(memory_repo: MemoryRepository) -> list:
    @tool
    def memory_search(
        query: str,
        memory_type: str = "",
        limit: int = 5,
        threshold: float = 0.45,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Mia's long-term memory for preferences, facts, plans, goals, and prior decisions."""
        rows = memory_repo.search(
            chat_id=runtime.context.chat_id,
            query=query,
            limit=max(1, min(limit, 8)),
            threshold=max(0.0, min(threshold, 1.0)),
            memory_type=memory_type.strip(),
        )
        return _format_memory_search(rows)

    @tool
    def memory_recent(
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List Mia's most recent durable memories for this chat."""
        rows = memory_repo.recent(
            chat_id=runtime.context.chat_id,
            limit=max(1, min(limit, 10)),
        )
        return _format_memory_recent(rows)

    @tool
    def memory_write(
        content: str,
        memory_type: str = "general",
        title: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Write a durable memory when the user asks Mia to remember a stable preference, goal, plan, or fact."""
        saved = memory_repo.write(
            chat_id=runtime.context.chat_id,
            content=content,
            memory_type=memory_type or "general",
            title=title.strip(),
            tags=tags or [],
            importance=max(1, min(importance, 5)),
            source_text=content,
        )
        title_val = saved["title"] or "không có tiêu đề"
        return (
            "Đã lưu memory.\n"
            f"Loại: {saved['memory_type']}\n"
            f"Tiêu đề: {title_val}\n"
            f"Nội dung: {saved['content']}"
        )

    return [memory_search, memory_recent, memory_write]
