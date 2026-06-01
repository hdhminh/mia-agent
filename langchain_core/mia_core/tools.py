from __future__ import annotations

from collections.abc import Callable
from typing import Any

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
        return _run_gateway_tool(
            tool_gateway,
            "weather.get",
            {"location": location},
            runtime,
        )

    @tool
    def gold_get_price(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the latest SJC or 9999 gold price."""
        return _run_gateway_tool(tool_gateway, "gold.get_price", {}, runtime)

    @tool
    def news_get(
        topic: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get today's latest news. Use when the user asks for latest or current news."""
        return _run_gateway_tool(
            tool_gateway,
            "news.get",
            {"topic": topic},
            runtime,
        )

    @tool
    def search_web(
        query: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search the web for current facts, references, and links."""
        return _run_gateway_tool(
            tool_gateway,
            "search.web",
            {"query": query},
            runtime,
        )

    @tool("calendar_help")
    def calendar_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Google Calendar capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "calendar.help", {}, runtime)

    @tool("calendar_list_today")
    def calendar_list_today_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List today's Google Calendar events."""
        return _run_gateway_tool(tool_gateway, "calendar.list_today", {}, runtime)

    @tool("calendar_list_tomorrow")
    def calendar_list_tomorrow_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List tomorrow's Google Calendar events."""
        return _run_gateway_tool(tool_gateway, "calendar.list_tomorrow", {}, runtime)

    @tool("calendar_find_event")
    def calendar_find_event_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Find Google Calendar events by date, keyword, or schedule request."""
        text = _normalize_instruction("calendar", "tim su kien", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.find_event",
            {"instruction": text},
            runtime,
        )

    @tool("calendar_create_event")
    def calendar_create_event_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Calendar event from a natural-language instruction."""
        text = _normalize_instruction("calendar", "tao lich", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.create_event",
            {"instruction": text},
            runtime,
        )

    @tool("calendar_delete_event")
    def calendar_delete_event_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete or cancel a Google Calendar event from a natural-language instruction."""
        text = _normalize_instruction("calendar", "xoa lich", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.delete_event",
            {"instruction": text},
            runtime,
        )

    @tool("calendar_check_availability")
    def calendar_check_availability_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Check Google Calendar availability or free/busy time."""
        text = _normalize_instruction("calendar", "kiem tra lich ranh", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.check_availability",
            {"instruction": text},
            runtime,
        )

    @tool("gmail_help")
    def gmail_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Gmail capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "gmail.help", {}, runtime)

    @tool("gmail_list_inbox")
    def gmail_list_inbox_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List the latest emails in Gmail inbox."""
        return _run_gateway_tool(tool_gateway, "gmail.list_inbox", {}, runtime)

    @tool("gmail_read_email")
    def gmail_read_email_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the contents of a specific Gmail email."""
        text = _normalize_instruction("gmail", "doc email", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.read_email",
            {"instruction": text},
            runtime,
        )

    @tool("gmail_search_email")
    def gmail_search_email_tool(
        query: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Gmail emails by keyword, sender, or subject."""
        text = _normalize_instruction("gmail", "tim email", query)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.search_email",
            {"query": query, "instruction": text},
            runtime,
        )

    @tool("gmail_send_email")
    def gmail_send_email_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Send a Gmail email from a natural-language instruction."""
        text = _normalize_instruction("gmail", "gui email", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.send_email",
            {"instruction": text},
            runtime,
        )

    @tool("gmail_draft_email")
    def gmail_draft_email_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Gmail draft from a natural-language instruction."""
        text = _normalize_instruction("gmail", "soan email", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.draft_email",
            {"instruction": text},
            runtime,
        )

    @tool("gmail_reply_email")
    def gmail_reply_email_tool(
        instruction: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Reply to a Gmail email from a natural-language instruction."""
        text = _normalize_instruction("gmail", "tra loi email", instruction)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.reply_email",
            {"instruction": text},
            runtime,
        )

    @tool("drive_help")
    def drive_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Google Drive capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "drive.help", {}, runtime)

    @tool("drive_list_files")
    def drive_list_files_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List recent files in Google Drive."""
        return _run_gateway_tool(tool_gateway, "drive.list_files", {}, runtime)

    @tool("drive_search_file")
    def drive_search_file_tool(
        query: str,
        mime_type: str = "",
        limit: int = 10,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search files in Google Drive by name and optional mime type."""
        text = _normalize_instruction("drive", "tim file", query)
        return _run_gateway_tool(
            tool_gateway,
            "drive.search_file",
            {
                "query": query,
                "fileName": query,
                "mimeType": mime_type,
                "limit": max(1, min(limit, 20)),
                "instruction": text,
            },
            runtime,
        )

    def _instruction_tool(
        *,
        public_name: str,
        gateway_name: str,
        description: str,
        default_instruction: str,
    ) -> Callable[..., str]:
        def _inner(
            instruction: str,
            runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
        ) -> str:
            text = _normalize_instruction(public_name.split("_", 1)[0], default_instruction, instruction)
            return _run_gateway_tool(
                tool_gateway,
                gateway_name,
                {"instruction": text},
                runtime,
            )

        _inner.__doc__ = description
        return tool(public_name)(_inner)

    drive_get_file_info_tool = _instruction_tool(
        public_name="drive_get_file_info",
        gateway_name="drive.get_file_info",
        description="Get detailed information for a Google Drive file or folder.",
        default_instruction="xem chi tiet file",
    )
    drive_create_folder_tool = _instruction_tool(
        public_name="drive_create_folder",
        gateway_name="drive.create_folder",
        description="Create a Google Drive folder from a natural-language instruction.",
        default_instruction="tao folder",
    )
    drive_create_file_tool = _instruction_tool(
        public_name="drive_create_file",
        gateway_name="drive.create_file",
        description="Create a Google Drive file from a natural-language instruction.",
        default_instruction="tao file",
    )
    drive_upload_file_tool = _instruction_tool(
        public_name="drive_upload_file",
        gateway_name="drive.upload_file",
        description="Upload a file to Google Drive from a natural-language instruction.",
        default_instruction="upload file",
    )
    drive_download_file_tool = _instruction_tool(
        public_name="drive_download_file",
        gateway_name="drive.download_file",
        description="Download a Google Drive file from a natural-language instruction.",
        default_instruction="tai file",
    )
    drive_share_file_tool = _instruction_tool(
        public_name="drive_share_file",
        gateway_name="drive.share_file",
        description="Share a Google Drive file or folder from a natural-language instruction.",
        default_instruction="share file",
    )
    drive_move_file_tool = _instruction_tool(
        public_name="drive_move_file",
        gateway_name="drive.move_file",
        description="Move a Google Drive file or folder from a natural-language instruction.",
        default_instruction="di chuyen file",
    )
    drive_rename_file_tool = _instruction_tool(
        public_name="drive_rename_file",
        gateway_name="drive.rename_file",
        description="Rename a Google Drive file or folder from a natural-language instruction.",
        default_instruction="doi ten file",
    )
    drive_copy_file_tool = _instruction_tool(
        public_name="drive_copy_file",
        gateway_name="drive.copy_file",
        description="Copy a Google Drive file from a natural-language instruction.",
        default_instruction="copy file",
    )
    drive_delete_file_tool = _instruction_tool(
        public_name="drive_delete_file",
        gateway_name="drive.delete_file",
        description="Delete a Google Drive file from a natural-language instruction.",
        default_instruction="xoa file",
    )
    drive_delete_folder_tool = _instruction_tool(
        public_name="drive_delete_folder",
        gateway_name="drive.delete_folder",
        description="Delete a Google Drive folder from a natural-language instruction.",
        default_instruction="xoa folder",
    )
    drive_export_file_tool = _instruction_tool(
        public_name="drive_export_file",
        gateway_name="drive.export_file",
        description="Export a Google Drive document to another format from a natural-language instruction.",
        default_instruction="export file",
    )

    @tool("docs_help")
    def docs_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Google Docs capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "docs.help", {}, runtime)

    @tool("docs_search_doc")
    def docs_search_doc_tool(
        query: str,
        limit: int = 10,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Docs documents by title or keyword."""
        text = _normalize_instruction("docs", "tim doc", query)
        return _run_gateway_tool(
            tool_gateway,
            "docs.search_doc",
            {"query": query, "docName": query, "limit": max(1, min(limit, 20)), "instruction": text},
            runtime,
        )

    docs_read_doc_tool = _instruction_tool(
        public_name="docs_read_doc",
        gateway_name="docs.read_doc",
        description="Read the content of a Google Docs document from a natural-language instruction.",
        default_instruction="xem doc",
    )
    docs_create_doc_tool = _instruction_tool(
        public_name="docs_create_doc",
        gateway_name="docs.create_doc",
        description="Create a Google Docs document from a natural-language instruction.",
        default_instruction="tao doc",
    )
    docs_append_doc_tool = _instruction_tool(
        public_name="docs_append_doc",
        gateway_name="docs.append_doc",
        description="Append content to a Google Docs document from a natural-language instruction.",
        default_instruction="them vao doc",
    )
    docs_delete_doc_tool = _instruction_tool(
        public_name="docs_delete_doc",
        gateway_name="docs.delete_doc",
        description="Delete a Google Docs document from a natural-language instruction.",
        default_instruction="xoa doc",
    )

    @tool("sheets_help")
    def sheets_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show Google Sheets capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "sheets.help", {}, runtime)

    @tool("sheets_search_sheet")
    def sheets_search_sheet_tool(
        query: str,
        limit: int = 10,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Sheets spreadsheets by title or keyword."""
        text = _normalize_instruction("sheets", "tim sheet", query)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.search_sheet",
            {"query": query, "sheetName": query, "limit": max(1, min(limit, 20)), "instruction": text},
            runtime,
        )

    sheets_read_sheet_tool = _instruction_tool(
        public_name="sheets_read_sheet",
        gateway_name="sheets.read_sheet",
        description="Read data from a Google Sheets spreadsheet from a natural-language instruction.",
        default_instruction="xem sheet",
    )
    sheets_create_sheet_tool = _instruction_tool(
        public_name="sheets_create_sheet",
        gateway_name="sheets.create_sheet",
        description="Create a Google Sheets spreadsheet from a natural-language instruction.",
        default_instruction="tao sheet",
    )
    sheets_append_row_tool = _instruction_tool(
        public_name="sheets_append_row",
        gateway_name="sheets.append_row",
        description="Append a row to Google Sheets from a natural-language instruction.",
        default_instruction="them dong vao sheet",
    )
    sheets_update_cell_tool = _instruction_tool(
        public_name="sheets_update_cell",
        gateway_name="sheets.update_cell",
        description="Update a Google Sheets cell from a natural-language instruction.",
        default_instruction="cap nhat sheet",
    )
    sheets_delete_sheet_tool = _instruction_tool(
        public_name="sheets_delete_sheet",
        gateway_name="sheets.delete_sheet",
        description="Delete a Google Sheets spreadsheet from a natural-language instruction.",
        default_instruction="xoa sheet",
    )

    @tool
    def shortlink_create(
        url: str,
        ttl: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a short link through n8n. The ttl can be like 24h, 7d, 30d, or 'vinh vien'."""
        return _run_gateway_tool(
            tool_gateway,
            "shortlink.create",
            {"url": url, "ttl": ttl},
            runtime,
        )

    return [
        memory_search,
        memory_recent,
        memory_write,
        weather_get,
        gold_get_price,
        news_get,
        search_web,
        calendar_help_tool,
        calendar_list_today_tool,
        calendar_list_tomorrow_tool,
        calendar_find_event_tool,
        calendar_create_event_tool,
        calendar_delete_event_tool,
        calendar_check_availability_tool,
        gmail_help_tool,
        gmail_list_inbox_tool,
        gmail_read_email_tool,
        gmail_search_email_tool,
        gmail_send_email_tool,
        gmail_draft_email_tool,
        gmail_reply_email_tool,
        drive_help_tool,
        drive_list_files_tool,
        drive_search_file_tool,
        drive_get_file_info_tool,
        drive_create_folder_tool,
        drive_create_file_tool,
        drive_upload_file_tool,
        drive_download_file_tool,
        drive_share_file_tool,
        drive_move_file_tool,
        drive_rename_file_tool,
        drive_copy_file_tool,
        drive_delete_file_tool,
        drive_delete_folder_tool,
        drive_export_file_tool,
        docs_help_tool,
        docs_search_doc_tool,
        docs_read_doc_tool,
        docs_create_doc_tool,
        docs_append_doc_tool,
        docs_delete_doc_tool,
        sheets_help_tool,
        sheets_search_sheet_tool,
        sheets_read_sheet_tool,
        sheets_create_sheet_tool,
        sheets_append_row_tool,
        sheets_update_cell_tool,
        sheets_delete_sheet_tool,
        shortlink_create,
    ]
