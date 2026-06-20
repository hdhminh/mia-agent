from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _run_gateway_tool, _normalize_instruction


def get_google_tools(tool_gateway: N8nToolGatewayClient) -> list:
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
        query: str = "",
        date_from: str = "",
        date_to: str = "",
        calendar_id: str = "",
        limit: int = 5,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Find Google Calendar events by structured query/date filters or a natural-language instruction."""
        text = _normalize_instruction("calendar", "tim su kien", instruction or query)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.find_event",
            {
                "query": query.strip(),
                "dateFrom": date_from.strip(),
                "dateTo": date_to.strip(),
                "calendarId": calendar_id.strip(),
                "limit": max(1, min(limit, 10)),
                "instruction": text,
            },
            runtime,
        )

    @tool("calendar_create_event")
    def calendar_create_event_tool(
        title: str = "",
        start_at: str = "",
        end_at: str = "",
        timezone: str = "",
        description: str = "",
        location: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Calendar event from structured fields or a natural-language instruction."""
        text = _normalize_instruction("calendar", "tao lich", instruction or title)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.create_event",
            {
                "title": title.strip(),
                "summary": title.strip(),
                "startAt": start_at.strip(),
                "endAt": end_at.strip(),
                "timezone": timezone.strip(),
                "description": description.strip(),
                "location": location.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("calendar_delete_event")
    def calendar_delete_event_tool(
        event_id: str = "",
        query: str = "",
        calendar_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete or cancel a Google Calendar event by structured event id or a natural-language instruction."""
        text = _normalize_instruction(
            "calendar",
            "xoa lich",
            instruction or query or event_id,
        )
        return _run_gateway_tool(
            tool_gateway,
            "calendar.delete_event",
            {
                "eventId": event_id.strip(),
                "query": query.strip(),
                "calendarId": calendar_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("calendar_check_availability")
    def calendar_check_availability_tool(
        date: str = "",
        start_at: str = "",
        end_at: str = "",
        timezone: str = "",
        calendar_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Check Google Calendar availability using structured time fields or a natural-language instruction."""
        text = _normalize_instruction(
            "calendar",
            "kiem tra lich ranh",
            instruction or date or start_at or end_at,
        )
        return _run_gateway_tool(
            tool_gateway,
            "calendar.check_availability",
            {
                "date": date.strip(),
                "startAt": start_at.strip(),
                "endAt": end_at.strip(),
                "timezone": timezone.strip(),
                "calendarId": calendar_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("calendar_find_free_slot")
    def calendar_find_free_slot_tool(
        date: str = "",
        start_at: str = "",
        end_at: str = "",
        duration_minutes: int = 60,
        calendar_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Find free time slots in Google Calendar."""
        text = _normalize_instruction("calendar", "tim khoang trong", instruction or date or start_at or end_at)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.find_free_slot",
            {
                "date": date.strip(),
                "startAt": start_at.strip(),
                "endAt": end_at.strip(),
                "durationMinutes": max(15, min(duration_minutes, 1440)),
                "calendarId": calendar_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("calendar_reschedule_event")
    def calendar_reschedule_event_tool(
        event_id: str = "",
        query: str = "",
        start_at: str = "",
        end_at: str = "",
        timezone: str = "",
        calendar_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Reschedule an existing Google Calendar event."""
        text = _normalize_instruction("calendar", "doi lich", instruction or query or event_id)
        return _run_gateway_tool(
            tool_gateway,
            "calendar.reschedule_event",
            {
                "eventId": event_id.strip(),
                "query": query.strip(),
                "startAt": start_at.strip(),
                "endAt": end_at.strip(),
                "timezone": timezone.strip(),
                "calendarId": calendar_id.strip(),
                "instruction": text,
            },
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
        query: str = "",
        message_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the contents of a Gmail email by structured query or message id."""
        text = _normalize_instruction("gmail", "doc email", instruction or query or message_id)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.read_email",
            {
                "query": query.strip(),
                "messageId": message_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_search_email")
    def gmail_search_email_tool(
        query: str,
        sender: str = "",
        subject: str = "",
        limit: int = 3,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Gmail emails by keyword, sender, or subject."""
        structured_bits = [part.strip() for part in [query, sender, subject] if part and part.strip()]
        text = _normalize_instruction("gmail", "tim email", " ".join(structured_bits) or query)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.search_email",
            {
                "query": query.strip(),
                "sender": sender.strip(),
                "subject": subject.strip(),
                "limit": max(1, min(limit, 5)),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_search_by_sender")
    def gmail_search_by_sender_tool(
        sender: str,
        query: str = "",
        subject: str = "",
        limit: int = 3,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Gmail emails by sender, with optional keyword or subject filters."""
        structured_bits = [part.strip() for part in [sender, query, subject] if part and part.strip()]
        text = _normalize_instruction("gmail", "tim email theo nguoi gui", " ".join(structured_bits) or sender)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.search_by_sender",
            {
                "query": query.strip() or sender.strip(),
                "sender": sender.strip(),
                "subject": subject.strip(),
                "limit": max(1, min(limit, 5)),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_mark_read")
    def gmail_mark_read_tool(
        message_id: str = "",
        query: str = "",
        sender: str = "",
        subject: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Mark Gmail messages as read."""
        text = _normalize_instruction("gmail", "danh dau da doc", instruction or query or sender or subject or message_id)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.mark_read",
            {
                "messageId": message_id.strip(),
                "query": query.strip(),
                "sender": sender.strip(),
                "subject": subject.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_archive")
    def gmail_archive_tool(
        message_id: str = "",
        query: str = "",
        sender: str = "",
        subject: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Archive Gmail messages by removing them from Inbox."""
        text = _normalize_instruction("gmail", "luu tru email", instruction or query or sender or subject or message_id)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.archive",
            {
                "messageId": message_id.strip(),
                "query": query.strip(),
                "sender": sender.strip(),
                "subject": subject.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_send_email")
    def gmail_send_email_tool(
        to: str = "",
        subject: str = "",
        body: str = "",
        cc: str = "",
        bcc: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Send a Gmail email from structured fields or a natural-language instruction."""
        structured_text = " ".join(part.strip() for part in [to, subject] if part and part.strip())
        text = _normalize_instruction("gmail", "gui email", instruction or structured_text)
        return _run_gateway_tool(
            tool_gateway,
            "gmail.send_email",
            {
                "to": to.strip(),
                "toEmail": to.strip(),
                "subject": subject.strip(),
                "body": body.strip(),
                "cc": cc.strip(),
                "bcc": bcc.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_draft_email")
    def gmail_draft_email_tool(
        to: str = "",
        subject: str = "",
        body: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Gmail draft from structured fields or a natural-language instruction."""
        text = _normalize_instruction(
            "gmail",
            "soan email",
            instruction or " ".join(part for part in [to, subject] if part).strip(),
        )
        return _run_gateway_tool(
            tool_gateway,
            "gmail.draft_email",
            {
                "to": to.strip(),
                "toEmail": to.strip(),
                "subject": subject.strip(),
                "body": body.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("gmail_reply_email")
    def gmail_reply_email_tool(
        message_id: str = "",
        body: str = "",
        search_query: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Reply to a Gmail email from structured fields or a natural-language instruction."""
        text = _normalize_instruction(
            "gmail",
            "tra loi email",
            instruction or search_query or message_id,
        )
        return _run_gateway_tool(
            tool_gateway,
            "gmail.reply_email",
            {
                "messageId": message_id.strip(),
                "searchQuery": search_query.strip(),
                "body": body.strip(),
                "instruction": text,
            },
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
        folder_id: str = "",
        limit: int = 5,
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
                "folderId": folder_id,
                "limit": max(1, min(limit, 8)),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_get_file_info")
    def drive_get_file_info_tool(
        file_id: str = "",
        file_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get detailed information for a Google Drive file or folder."""
        text = _normalize_instruction("drive", "xem chi tiet file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.get_file_info",
            {
                "fileId": file_id.strip(),
                "fileName": file_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_create_folder")
    def drive_create_folder_tool(
        name: str = "",
        parent_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Drive folder from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "tao folder", instruction or name)
        return _run_gateway_tool(
            tool_gateway,
            "drive.create_folder",
            {
                "folderName": name.strip(),
                "name": name.strip(),
                "folderId": parent_id.strip(),
                "parentId": parent_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_create_file")
    def drive_create_file_tool(
        name: str = "",
        content: str = "",
        mime_type: str = "",
        parent_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Drive file from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "tao file", instruction or name)
        return _run_gateway_tool(
            tool_gateway,
            "drive.create_file",
            {
                "name": name.strip(),
                "fileName": name.strip(),
                "content": content,
                "mimeType": mime_type.strip(),
                "parentId": parent_id.strip(),
                "folderId": parent_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_upload_file")
    def drive_upload_file_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Upload a Telegram attachment to Google Drive from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "upload file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.upload_file",
            {
                "fileId": file_id.strip(),
                "telegramFileId": file_id.strip(),
                "fileName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "folderId": folder_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_download_file")
    def drive_download_file_tool(
        file_id: str = "",
        file_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Download a Google Drive file from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "tai file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.download_file",
            {
                "fileId": file_id.strip(),
                "targetId": file_id.strip(),
                "fileName": file_name.strip(),
                "targetName": file_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_share_file")
    def drive_share_file_tool(
        file_id: str = "",
        file_name: str = "",
        email: str = "",
        role: str = "reader",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Share a Google Drive file or folder from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "share file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.share_file",
            {
                "fileId": file_id.strip(),
                "fileName": file_name.strip(),
                "email": email.strip(),
                "role": role.strip() or "reader",
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_move_file")
    def drive_move_file_tool(
        file_id: str = "",
        file_name: str = "",
        target_folder_id: str = "",
        target_folder_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Move a Google Drive file or folder from structured fields or a natural-language instruction."""
        text = _normalize_instruction(
            "drive",
            "di chuyen file",
            instruction or file_name or file_id,
        )
        return _run_gateway_tool(
            tool_gateway,
            "drive.move_file",
            {
                "fileId": file_id.strip(),
                "targetId": file_id.strip(),
                "fileName": file_name.strip(),
                "targetFolderId": target_folder_id.strip(),
                "folderId": target_folder_id.strip(),
                "targetFolderName": target_folder_name.strip(),
                "folderName": target_folder_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_rename_file")
    def drive_rename_file_tool(
        file_id: str = "",
        file_name: str = "",
        new_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Rename a Google Drive file or folder from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "doi ten file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.rename_file",
            {
                "fileId": file_id.strip(),
                "targetId": file_id.strip(),
                "fileName": file_name.strip(),
                "targetName": file_name.strip(),
                "newName": new_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_copy_file")
    def drive_copy_file_tool(
        file_id: str = "",
        file_name: str = "",
        new_name: str = "",
        parent_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Copy a Google Drive file from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "copy file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.copy_file",
            {
                "fileId": file_id.strip(),
                "fileName": file_name.strip(),
                "newName": new_name.strip(),
                "parentId": parent_id.strip(),
                "targetFolderId": parent_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_delete_file")
    def drive_delete_file_tool(
        file_id: str = "",
        file_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Drive file from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "xoa file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.delete_file",
            {
                "fileId": file_id.strip(),
                "fileName": file_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_delete_folder")
    def drive_delete_folder_tool(
        folder_id: str = "",
        folder_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Drive folder from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "xoa folder", instruction or folder_name or folder_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.delete_folder",
            {
                "folderId": folder_id.strip(),
                "targetId": folder_id.strip(),
                "folderName": folder_name.strip(),
                "targetName": folder_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("drive_export_file")
    def drive_export_file_tool(
        file_id: str = "",
        file_name: str = "",
        mime_type: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Export a Google Drive document from structured fields or a natural-language instruction."""
        text = _normalize_instruction("drive", "export file", instruction or file_name or file_id)
        return _run_gateway_tool(
            tool_gateway,
            "drive.export_file",
            {
                "fileId": file_id.strip(),
                "targetId": file_id.strip(),
                "fileName": file_name.strip(),
                "targetName": file_name.strip(),
                "mimeType": mime_type.strip(),
                "format": mime_type.strip(),
                "instruction": text,
            },
            runtime,
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
        folder_id: str = "",
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Docs documents by title or keyword."""
        text = _normalize_instruction("docs", "tim doc", query)
        return _run_gateway_tool(
            tool_gateway,
            "docs.search_doc",
            {
                "query": query,
                "docName": query,
                "folderId": folder_id,
                "limit": max(1, min(limit, 8)),
                "instruction": text,
            },
            runtime,
        )

    @tool("docs_read_doc")
    def docs_read_doc_tool(
        document_id: str = "",
        doc_name: str = "",
        max_chars: int = 1000,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the content of a Google Docs document from structured fields or a natural-language instruction."""
        text = _normalize_instruction("docs", "xem doc", instruction or doc_name or document_id)
        return _run_gateway_tool(
            tool_gateway,
            "docs.read_doc",
            {
                "docId": document_id.strip(),
                "documentId": document_id.strip(),
                "docName": doc_name.strip(),
                "maxChars": max(200, min(max_chars, 3000)),
                "instruction": text,
            },
            runtime,
        )

    @tool("docs_create_doc")
    def docs_create_doc_tool(
        title: str = "",
        content: str = "",
        folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Docs document from structured fields or a natural-language instruction."""
        text = _normalize_instruction("docs", "tao doc", instruction or title)
        return _run_gateway_tool(
            tool_gateway,
            "docs.create_doc",
            {
                "title": title.strip(),
                "content": content.strip(),
                "folderId": folder_id.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("docs_append_doc")
    def docs_append_doc_tool(
        document_id: str = "",
        doc_name: str = "",
        content: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Append content to a Google Docs document from structured fields or a natural-language instruction."""
        text = _normalize_instruction("docs", "them vao doc", instruction or doc_name or document_id)
        return _run_gateway_tool(
            tool_gateway,
            "docs.append_doc",
            {
                "docId": document_id.strip(),
                "documentId": document_id.strip(),
                "docName": doc_name.strip(),
                "content": content.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("docs_update_doc")
    def docs_update_doc_tool(
        document_id: str = "",
        doc_name: str = "",
        content: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Replace or update the content of a Google Docs document."""
        text = _normalize_instruction("docs", "cap nhat doc", instruction or doc_name or document_id)
        return _run_gateway_tool(
            tool_gateway,
            "docs.update_doc",
            {
                "docId": document_id.strip(),
                "documentId": document_id.strip(),
                "docName": doc_name.strip(),
                "content": content.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("docs_delete_doc")
    def docs_delete_doc_tool(
        document_id: str = "",
        doc_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Docs document from structured fields or a natural-language instruction."""
        text = _normalize_instruction("docs", "xoa doc", instruction or doc_name or document_id)
        return _run_gateway_tool(
            tool_gateway,
            "docs.delete_doc",
            {
                "docId": document_id.strip(),
                "documentId": document_id.strip(),
                "docName": doc_name.strip(),
                "instruction": text,
            },
            runtime,
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
        folder_id: str = "",
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Sheets spreadsheets by title or keyword."""
        text = _normalize_instruction("sheets", "tim sheet", query)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.search_sheet",
            {
                "query": query,
                "sheetName": query,
                "folderId": folder_id,
                "limit": max(1, min(limit, 8)),
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_read_sheet")
    def sheets_read_sheet_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        range_name: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read data from a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        text = _normalize_instruction("sheets", "xem sheet", instruction or sheet_name or spreadsheet_id)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.read_sheet",
            {
                "spreadsheetId": spreadsheet_id.strip(),
                "sheetName": sheet_name.strip(),
                "range": range_name.strip(),
                "sheetTab": sheet_tab.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_read_range")
    def sheets_read_range_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        range_name: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read a specific range from Google Sheets."""
        text = _normalize_instruction("sheets", "xem vung sheet", instruction or range_name or sheet_name or spreadsheet_id)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.read_sheet",
            {
                "spreadsheetId": spreadsheet_id.strip(),
                "sheetName": sheet_name.strip(),
                "range": range_name.strip(),
                "sheetTab": sheet_tab.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_create_sheet")
    def sheets_create_sheet_tool(
        title: str = "",
        sheet_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        text = _normalize_instruction("sheets", "tao sheet", instruction or title or sheet_name)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.create_sheet",
            {
                "title": title.strip() or sheet_name.strip(),
                "sheetTitle": title.strip() or sheet_name.strip(),
                "sheetName": sheet_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_append_row")
    def sheets_append_row_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        values: list[str] | None = None,
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Append a row to Google Sheets from structured fields or a natural-language instruction."""
        text = _normalize_instruction("sheets", "them dong vao sheet", instruction or sheet_name or spreadsheet_id)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.append_row",
            {
                "spreadsheetId": spreadsheet_id.strip(),
                "sheetName": sheet_name.strip(),
                "sheetTab": sheet_tab.strip(),
                "values": values or [],
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_update_cell")
    def sheets_update_cell_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        cell: str = "",
        value: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Update a Google Sheets cell from structured fields or a natural-language instruction."""
        text = _normalize_instruction("sheets", "cap nhat sheet", instruction or sheet_name or spreadsheet_id)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.update_cell",
            {
                "spreadsheetId": spreadsheet_id.strip(),
                "sheetName": sheet_name.strip(),
                "sheetTab": sheet_tab.strip(),
                "cell": cell.strip(),
                "value": value.strip(),
                "instruction": text,
            },
            runtime,
        )

    @tool("sheets_update_range")
    def sheets_update_range_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        range_name: str = "",
        content: str = "",
        values: list[list[str]] | None = None,
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Update a range in Google Sheets."""
        text = _normalize_instruction("sheets", "cap nhat vung sheet", instruction or range_name or sheet_name or spreadsheet_id)
        payload: dict[str, Any] = {
            "spreadsheetId": spreadsheet_id.strip(),
            "sheetName": sheet_name.strip(),
            "range": range_name.strip(),
            "sheetTab": sheet_tab.strip(),
            "content": content.strip(),
            "instruction": text,
        }
        if values is not None:
            payload["values"] = values
        return _run_gateway_tool(
            tool_gateway,
            "sheets.update_range",
            payload,
            runtime,
        )

    @tool("sheets_delete_sheet")
    def sheets_delete_sheet_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        text = _normalize_instruction("sheets", "xoa sheet", instruction or sheet_name or spreadsheet_id)
        return _run_gateway_tool(
            tool_gateway,
            "sheets.delete_sheet",
            {
                "spreadsheetId": spreadsheet_id.strip(),
                "sheetName": sheet_name.strip(),
                "instruction": text,
            },
            runtime,
        )

    return [
        calendar_help_tool,
        calendar_list_today_tool,
        calendar_list_tomorrow_tool,
        calendar_find_event_tool,
        calendar_find_free_slot_tool,
        calendar_create_event_tool,
        calendar_reschedule_event_tool,
        calendar_delete_event_tool,
        calendar_check_availability_tool,
        gmail_help_tool,
        gmail_list_inbox_tool,
        gmail_read_email_tool,
        gmail_search_email_tool,
        gmail_search_by_sender_tool,
        gmail_mark_read_tool,
        gmail_archive_tool,
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
        docs_update_doc_tool,
        docs_delete_doc_tool,
        sheets_help_tool,
        sheets_search_sheet_tool,
        sheets_read_sheet_tool,
        sheets_read_range_tool,
        sheets_create_sheet_tool,
        sheets_append_row_tool,
        sheets_update_cell_tool,
        sheets_update_range_tool,
        sheets_delete_sheet_tool,
    ]
