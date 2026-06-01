from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from mia_core.memory import MemoryRepository
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


def build_tools(
    *,
    memory_repo: MemoryRepository,
    tool_gateway: N8nToolGatewayClient,
) -> list:
    @tool
    def memory_search(
        query: str,
        memory_type: str = "",
        limit: int = 5,
        threshold: float = 0.45,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Mia's long-term memory for user preferences, goals, plans, facts, and prior decisions."""
        rows = memory_repo.search(
            chat_id=runtime.context.chat_id,
            query=query,
            limit=max(1, min(limit, 8)),
            threshold=max(0.0, min(threshold, 1.0)),
            memory_type=memory_type.strip(),
        )
        return _format_memory_search(rows)

    @tool
    def memory_write(
        content: str,
        memory_type: str = "general",
        title: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Write a durable memory when the user asks Mia to remember something, or when a stable preference, goal, plan, or fact should be stored."""
        saved = memory_repo.write(
            chat_id=runtime.context.chat_id,
            content=content,
            memory_type=memory_type or "general",
            title=title.strip(),
            tags=tags or [],
            importance=max(1, min(importance, 5)),
            source_text=content,
        )
        title = saved["title"] or "không có tiêu đề"
        return (
            "Đã lưu memory.\n"
            f"Loại: {saved['memory_type']}\n"
            f"Tiêu đề: {title}\n"
            f"Nội dung: {saved['content']}"
        )

    @tool
    def weather_get(
        location: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the current weather for a city or place."""
        return tool_gateway.run_tool(
            "weather.get",
            {"location": location},
            runtime.context,
        ).text

    @tool
    def gold_get_price(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the latest SJC or 9999 gold price."""
        return tool_gateway.run_tool("gold.get_price", {}, runtime.context).text

    @tool
    def news_get(
        topic: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get today's latest news. Use when the user asks for latest or current news."""
        return tool_gateway.run_tool(
            "news.get",
            {"topic": topic},
            runtime.context,
        ).text

    @tool
    def search_web(
        query: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search the web for general information or current facts."""
        return tool_gateway.run_tool(
            "search.web",
            {"query": query},
            runtime.context,
        ).text

    @tool
    def calendar_assistant(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Use Google Calendar through n8n for calendar tasks like checking schedule, creating events, deleting events, or checking availability."""
        return tool_gateway.run_tool(
            "calendar.assistant",
            {"instruction": instruction},
            runtime.context,
        ).text

    @tool
    def gmail_assistant(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Use Gmail through n8n for inbox lookup, email search, drafting, replying, or sending email."""
        return tool_gateway.run_tool(
            "gmail.assistant",
            {"instruction": instruction},
            runtime.context,
        ).text

    @tool
    def drive_assistant(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Use Google Drive through n8n for file lookup, upload, download, move, share, or delete tasks."""
        return tool_gateway.run_tool(
            "drive.assistant",
            {"instruction": instruction},
            runtime.context,
        ).text

    @tool
    def docs_assistant(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Use Google Docs through n8n for creating, reading, appending, searching, or deleting docs."""
        return tool_gateway.run_tool(
            "docs.assistant",
            {"instruction": instruction},
            runtime.context,
        ).text

    @tool
    def sheets_assistant(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Use Google Sheets through n8n for spreadsheet creation, reading, row append, cell update, search, or deletion."""
        return tool_gateway.run_tool(
            "sheets.assistant",
            {"instruction": instruction},
            runtime.context,
        ).text

    @tool
    def shortlink_create(
        url: str,
        ttl: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a short link through n8n. The ttl can be like 24h, 7d, 30d, or 'vinh vien'."""
        return tool_gateway.run_tool(
            "shortlink.create",
            {"url": url, "ttl": ttl},
            runtime.context,
        ).text

    return [
        memory_search,
        memory_write,
        weather_get,
        gold_get_price,
        news_get,
        search_web,
        calendar_assistant,
        gmail_assistant,
        drive_assistant,
        docs_assistant,
        sheets_assistant,
        shortlink_create,
    ]
