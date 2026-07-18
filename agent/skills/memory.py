from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime, tool

from agent.i18n import t
from agent.models import MiaContext
from agent.memory.repository import MemoryRepository
from agent.skills.common import _format_memory_search, _format_memory_recent


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
            owner_id=runtime.context.user_id,
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
            owner_id=runtime.context.user_id,
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
            owner_id=runtime.context.user_id,
            content=content,
            memory_type=memory_type or "general",
            title=title.strip(),
            tags=tags or [],
            importance=max(1, min(importance, 5)),
            source_text=content,
        )
        title_val = saved["title"] or t("skills.untitled", default="không có tiêu đề")
        return t(
            "skills.memory_saved",
            default="Đã lưu memory.\nLoại: {type}\nTiêu đề: {title}\nNội dung: {content}",
            type=saved['memory_type'],
            title=title_val,
            content=saved['content'],
        )

    @tool
    def memory_pending_proposals(
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List pending memory proposals waiting for user approval."""
        rows = memory_repo.list_pending_proposals(
            owner_id=runtime.context.user_id,
            chat_id=runtime.context.chat_id,
            limit=max(1, min(limit, 10)),
        )
        if not rows:
            return "Không có memory proposal nào đang chờ duyệt."
        lines = ["Memory proposal đang chờ duyệt:"]
        for row in rows:
            title = str(row.get("title") or "").strip()
            content = str(row.get("content") or "").strip()
            prefix = f"- #{row.get('id')}"
            if title:
                prefix += f" {title}:"
            lines.append(f"{prefix} {content}".strip())
        return "\n".join(lines)

    @tool
    def memory_accept_proposal(
        proposal_id: int,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Accept a pending memory proposal and save it as official long-term memory."""
        saved = memory_repo.accept_proposal(
            proposal_id=int(proposal_id),
            owner_id=runtime.context.user_id,
        )
        return f"Đã duyệt và lưu memory #{saved['id']}: {saved['content']}"

    @tool
    def memory_reject_proposal(
        proposal_id: int,
        reason: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Reject a pending memory proposal so Mia will not save it."""
        memory_repo.reject_proposal(
            proposal_id=int(proposal_id),
            owner_id=runtime.context.user_id,
            reason=reason,
        )
        return f"Đã bỏ qua memory proposal #{proposal_id}."

    return [
        memory_search,
        memory_recent,
        memory_write,
        memory_pending_proposals,
        memory_accept_proposal,
        memory_reject_proposal,
    ]
