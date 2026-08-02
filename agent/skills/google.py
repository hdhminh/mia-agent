from __future__ import annotations

from typing import Any
from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _run_gateway_tool, _with_instruction_fallback


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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.find_event",
            _with_instruction_fallback(
                "calendar",
                "tim su kien",
                {
                    "query": query.strip(),
                    "dateFrom": date_from.strip(),
                    "dateTo": date_to.strip(),
                    "calendarId": calendar_id.strip(),
                    "limit": max(1, min(limit, 10)),
                },
                instruction,
                query,
                date_from,
                date_to,
                calendar_id,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.create_event",
            _with_instruction_fallback(
                "calendar",
                "tao lich",
                {
                    "title": title.strip(),
                    "summary": title.strip(),
                    "startAt": start_at.strip(),
                    "endAt": end_at.strip(),
                    "timezone": timezone.strip(),
                    "description": description.strip(),
                    "location": location.strip(),
                },
                instruction,
                title,
                start_at,
                end_at,
                timezone,
                description,
                location,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.delete_event",
            _with_instruction_fallback(
                "calendar",
                "xoa lich",
                {
                    "eventId": event_id.strip(),
                    "query": query.strip(),
                    "calendarId": calendar_id.strip(),
                },
                instruction,
                event_id,
                query,
                calendar_id,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.check_availability",
            _with_instruction_fallback(
                "calendar",
                "kiem tra lich ranh",
                {
                    "date": date.strip(),
                    "startAt": start_at.strip(),
                    "endAt": end_at.strip(),
                    "timezone": timezone.strip(),
                    "calendarId": calendar_id.strip(),
                },
                instruction,
                date,
                start_at,
                end_at,
                timezone,
                calendar_id,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.find_free_slot",
            _with_instruction_fallback(
                "calendar",
                "tim khoang trong",
                {
                    "date": date.strip(),
                    "startAt": start_at.strip(),
                    "endAt": end_at.strip(),
                    "durationMinutes": max(15, min(duration_minutes, 1440)),
                    "calendarId": calendar_id.strip(),
                },
                instruction,
                date,
                start_at,
                end_at,
                calendar_id,
                duration_minutes,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "calendar.reschedule_event",
            _with_instruction_fallback(
                "calendar",
                "doi lich",
                {
                    "eventId": event_id.strip(),
                    "query": query.strip(),
                    "startAt": start_at.strip(),
                    "endAt": end_at.strip(),
                    "timezone": timezone.strip(),
                    "calendarId": calendar_id.strip(),
                },
                instruction,
                event_id,
                query,
                start_at,
                end_at,
                timezone,
                calendar_id,
            ),
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
        sender: str = "",
        subject: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the contents of a Gmail email by structured query or message id."""
        return _run_gateway_tool(
            tool_gateway,
            "gmail.read_email",
            _with_instruction_fallback(
                "gmail",
                "doc email",
                {
                    "query": query.strip(),
                    "messageId": message_id.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                },
                instruction,
                query,
                message_id,
                sender,
                subject,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.search_email",
            _with_instruction_fallback(
                "gmail",
                "tim email",
                {
                    "query": query.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                    "limit": max(1, min(limit, 5)),
                },
                "",
                query,
                sender,
                subject,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.search_by_sender",
            _with_instruction_fallback(
                "gmail",
                "tim email theo nguoi gui",
                {
                    "query": query.strip() or sender.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                    "limit": max(1, min(limit, 5)),
                },
                instruction,
                sender,
                query,
                subject,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.mark_read",
            _with_instruction_fallback(
                "gmail",
                "danh dau da doc",
                {
                    "messageId": message_id.strip(),
                    "query": query.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                },
                instruction,
                message_id,
                query,
                sender,
                subject,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.archive",
            _with_instruction_fallback(
                "gmail",
                "luu tru email",
                {
                    "messageId": message_id.strip(),
                    "query": query.strip(),
                    "sender": sender.strip(),
                    "subject": subject.strip(),
                },
                instruction,
                message_id,
                query,
                sender,
                subject,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.send_email",
            _with_instruction_fallback(
                "gmail",
                "gui email",
                {
                    "to": to.strip(),
                    "toEmail": to.strip(),
                    "subject": subject.strip(),
                    "body": body.strip(),
                    "cc": cc.strip(),
                    "bcc": bcc.strip(),
                },
                instruction,
                to,
                subject,
                body,
                cc,
                bcc,
            ),
            runtime,
        )

    @tool("gmail_draft_email")
    def gmail_draft_email_tool(
        to: str = "",
        subject: str = "",
        body: str = "",
        cc: str = "",
        bcc: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Gmail draft from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "gmail.draft_email",
            _with_instruction_fallback(
                "gmail",
                "soan email",
                {
                    "to": to.strip(),
                    "toEmail": to.strip(),
                    "subject": subject.strip(),
                    "body": body.strip(),
                    "cc": cc.strip(),
                    "bcc": bcc.strip(),
                },
                instruction,
                to,
                subject,
                body,
                cc,
                bcc,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "gmail.reply_email",
            _with_instruction_fallback(
                "gmail",
                "tra loi email",
                {
                    "messageId": message_id.strip(),
                    "searchQuery": search_query.strip(),
                    "body": body.strip(),
                },
                instruction,
                message_id,
                search_query,
                body,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.search_file",
            _with_instruction_fallback(
                "drive",
                "tim file",
                {
                    "query": query,
                    "fileName": query,
                    "mimeType": mime_type,
                    "folderId": folder_id,
                    "limit": max(1, min(limit, 8)),
                },
                "",
                query,
                mime_type,
                folder_id,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.get_file_info",
            _with_instruction_fallback(
                "drive",
                "xem chi tiet file",
                {
                    "fileId": file_id.strip(),
                    "fileName": file_name.strip(),
                },
                instruction,
                file_id,
                file_name,
            ),
            runtime,
        )

    @tool("drive_create_folder")
    def drive_create_folder_tool(
        name: str = "",
        target_name: str = "",
        parent_id: str = "",
        target_folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Drive folder from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.create_folder",
            _with_instruction_fallback(
                "drive",
                "tao folder",
                {
                    "folderName": name.strip() or target_name.strip(),
                    "name": name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or name.strip(),
                    "folderId": parent_id.strip() or target_folder_id.strip(),
                    "targetFolderId": target_folder_id.strip() or parent_id.strip(),
                    "parentId": parent_id.strip() or target_folder_id.strip(),
                },
                instruction,
                name,
                target_name,
                parent_id,
                target_folder_id,
            ),
            runtime,
        )

    @tool("drive_create_file")
    def drive_create_file_tool(
        name: str = "",
        target_name: str = "",
        content: str = "",
        mime_type: str = "",
        parent_id: str = "",
        target_folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Drive file from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.create_file",
            _with_instruction_fallback(
                "drive",
                "tao file",
                {
                    "name": name.strip() or target_name.strip(),
                    "fileName": name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or name.strip(),
                    "content": content,
                    "mimeType": mime_type.strip(),
                    "parentId": parent_id.strip() or target_folder_id.strip(),
                    "folderId": parent_id.strip() or target_folder_id.strip(),
                    "targetFolderId": target_folder_id.strip() or parent_id.strip(),
                },
                instruction,
                name,
                target_name,
                content,
                mime_type,
                parent_id,
                target_folder_id,
            ),
            runtime,
        )

    @tool("drive_upload_file")
    def drive_upload_file_tool(
        file_id: str = "",
        file_name: str = "",
        target_name: str = "",
        mime_type: str = "",
        folder_id: str = "",
        target_folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Upload a Telegram attachment to Google Drive from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.upload_file",
            _with_instruction_fallback(
                "drive",
                "upload file",
                {
                    "fileId": file_id.strip(),
                    "telegramFileId": file_id.strip(),
                    "fileName": file_name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or file_name.strip(),
                    "mimeType": mime_type.strip(),
                    "folderId": folder_id.strip() or target_folder_id.strip(),
                    "targetFolderId": target_folder_id.strip() or folder_id.strip(),
                },
                instruction,
                file_id,
                file_name,
                target_name,
                mime_type,
                folder_id,
                target_folder_id,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.download_file",
            _with_instruction_fallback(
                "drive",
                "tai file",
                {
                    "fileId": file_id.strip(),
                    "targetId": file_id.strip(),
                    "fileName": file_name.strip(),
                    "targetName": file_name.strip(),
                },
                instruction,
                file_id,
                file_name,
            ),
            runtime,
        )

    @tool("drive_share_file")
    def drive_share_file_tool(
        file_id: str = "",
        file_name: str = "",
        target_name: str = "",
        email: str = "",
        role: str = "reader",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Share a Google Drive file or folder from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.share_file",
            _with_instruction_fallback(
                "drive",
                "share file",
                {
                    "fileId": file_id.strip(),
                    "fileName": file_name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or file_name.strip(),
                    "email": email.strip(),
                    "role": role.strip() or "reader",
                },
                instruction,
                file_id,
                file_name,
                target_name,
                email,
                role,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.move_file",
            _with_instruction_fallback(
                "drive",
                "di chuyen file",
                {
                    "fileId": file_id.strip(),
                    "targetId": file_id.strip(),
                    "fileName": file_name.strip(),
                    "targetFolderId": target_folder_id.strip(),
                    "folderId": target_folder_id.strip(),
                    "targetFolderName": target_folder_name.strip(),
                    "folderName": target_folder_name.strip(),
                },
                instruction,
                file_id,
                file_name,
                target_folder_id,
                target_folder_name,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.rename_file",
            _with_instruction_fallback(
                "drive",
                "doi ten file",
                {
                    "fileId": file_id.strip(),
                    "targetId": file_id.strip(),
                    "fileName": file_name.strip(),
                    "targetName": file_name.strip(),
                    "newName": new_name.strip(),
                },
                instruction,
                file_id,
                file_name,
                new_name,
            ),
            runtime,
        )

    @tool("drive_copy_file")
    def drive_copy_file_tool(
        file_id: str = "",
        file_name: str = "",
        target_name: str = "",
        new_name: str = "",
        parent_id: str = "",
        target_folder_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Copy a Google Drive file from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.copy_file",
            _with_instruction_fallback(
                "drive",
                "copy file",
                {
                    "fileId": file_id.strip(),
                    "fileName": file_name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or file_name.strip(),
                    "newName": new_name.strip(),
                    "parentId": parent_id.strip(),
                    "targetFolderId": parent_id.strip(),
                    "targetFolderName": target_folder_name.strip(),
                },
                instruction,
                file_id,
                file_name,
                target_name,
                new_name,
                parent_id,
                target_folder_name,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.delete_file",
            _with_instruction_fallback(
                "drive",
                "xoa file",
                {
                    "fileId": file_id.strip(),
                    "fileName": file_name.strip(),
                },
                instruction,
                file_id,
                file_name,
            ),
            runtime,
        )

    @tool("drive_delete_folder")
    def drive_delete_folder_tool(
        folder_id: str = "",
        target_id: str = "",
        folder_name: str = "",
        target_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Drive folder from structured fields or a natural-language instruction."""
        return _run_gateway_tool(
            tool_gateway,
            "drive.delete_folder",
            _with_instruction_fallback(
                "drive",
                "xoa folder",
                {
                    "folderId": folder_id.strip() or target_id.strip(),
                    "targetId": target_id.strip() or folder_id.strip(),
                    "folderName": folder_name.strip() or target_name.strip(),
                    "targetName": target_name.strip() or folder_name.strip(),
                },
                instruction,
                folder_id,
                target_id,
                folder_name,
                target_name,
            ),
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
        return _run_gateway_tool(
            tool_gateway,
            "drive.export_file",
            _with_instruction_fallback(
                "drive",
                "export file",
                {
                    "fileId": file_id.strip(),
                    "targetId": file_id.strip(),
                    "fileName": file_name.strip(),
                    "targetName": file_name.strip(),
                    "mimeType": mime_type.strip(),
                    "format": mime_type.strip(),
                },
                instruction,
                file_id,
                file_name,
                mime_type,
            ),
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
        target_name: str = "",
        folder_id: str = "",
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Docs documents by title or keyword."""
        search_query = query.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.search_doc",
            _with_instruction_fallback(
                "docs",
                "tim doc",
                {
                    "query": search_query,
                    "docName": search_query,
                    "targetName": search_query,
                    "folderId": folder_id,
                    "limit": max(1, min(limit, 8)),
                },
                "",
                search_query,
                folder_id,
            ),
            runtime,
        )

    @tool("docs_read_doc")
    def docs_read_doc_tool(
        document_id: str = "",
        target_id: str = "",
        doc_name: str = "",
        target_name: str = "",
        max_chars: int = 1000,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the content of a Google Docs document from structured fields or a natural-language instruction."""
        doc_id = document_id.strip() or target_id.strip()
        doc_label = doc_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.read_doc",
            _with_instruction_fallback(
                "docs",
                "xem doc",
                {
                    "docId": doc_id,
                    "documentId": doc_id,
                    "targetId": doc_id,
                    "docName": doc_label,
                    "targetName": doc_label,
                    "maxChars": max(200, min(max_chars, 3000)),
                },
                instruction,
                doc_id,
                doc_label,
            ),
            runtime,
        )

    @tool("docs_create_doc")
    def docs_create_doc_tool(
        title: str = "",
        target_name: str = "",
        content: str = "",
        folder_id: str = "",
        target_folder_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Docs document from structured fields or a natural-language instruction."""
        doc_title = title.strip() or target_name.strip()
        folder = folder_id.strip() or target_folder_id.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.create_doc",
            _with_instruction_fallback(
                "docs",
                "tao doc",
                {
                    "title": doc_title,
                    "docTitle": doc_title,
                    "targetName": doc_title,
                    "content": content.strip(),
                    "folderId": folder,
                    "targetFolderId": folder,
                },
                instruction,
                doc_title,
                content,
                folder,
            ),
            runtime,
        )

    @tool("docs_append_doc")
    def docs_append_doc_tool(
        document_id: str = "",
        target_id: str = "",
        doc_name: str = "",
        target_name: str = "",
        content: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Append content to a Google Docs document from structured fields or a natural-language instruction."""
        doc_id = document_id.strip() or target_id.strip()
        doc_label = doc_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.append_doc",
            _with_instruction_fallback(
                "docs",
                "them vao doc",
                {
                    "docId": doc_id,
                    "documentId": doc_id,
                    "targetId": doc_id,
                    "docName": doc_label,
                    "targetName": doc_label,
                    "content": content.strip(),
                },
                instruction,
                doc_id,
                doc_label,
                content,
            ),
            runtime,
        )

    @tool("docs_update_doc")
    def docs_update_doc_tool(
        document_id: str = "",
        target_id: str = "",
        doc_name: str = "",
        target_name: str = "",
        content: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Replace or update the content of a Google Docs document."""
        doc_id = document_id.strip() or target_id.strip()
        doc_label = doc_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.update_doc",
            _with_instruction_fallback(
                "docs",
                "cap nhat doc",
                {
                    "docId": doc_id,
                    "documentId": doc_id,
                    "targetId": doc_id,
                    "docName": doc_label,
                    "targetName": doc_label,
                    "content": content.strip(),
                },
                instruction,
                doc_id,
                doc_label,
                content,
            ),
            runtime,
        )

    @tool("docs_delete_doc")
    def docs_delete_doc_tool(
        document_id: str = "",
        target_id: str = "",
        doc_name: str = "",
        target_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Docs document from structured fields or a natural-language instruction."""
        doc_id = document_id.strip() or target_id.strip()
        doc_label = doc_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "docs.delete_doc",
            _with_instruction_fallback(
                "docs",
                "xoa doc",
                {
                    "docId": doc_id,
                    "documentId": doc_id,
                    "targetId": doc_id,
                    "docName": doc_label,
                    "targetName": doc_label,
                },
                instruction,
                doc_id,
                doc_label,
            ),
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
        target_name: str = "",
        folder_id: str = "",
        limit: int = 5,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search Google Sheets spreadsheets by title or keyword."""
        search_query = query.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.search_sheet",
            _with_instruction_fallback(
                "sheets",
                "tim sheet",
                {
                    "query": search_query,
                    "sheetName": search_query,
                    "targetName": search_query,
                    "folderId": folder_id,
                    "limit": max(1, min(limit, 8)),
                },
                "",
                search_query,
                folder_id,
            ),
            runtime,
        )

    @tool("sheets_read_sheet")
    def sheets_read_sheet_tool(
        spreadsheet_id: str = "",
        target_id: str = "",
        sheet_name: str = "",
        target_name: str = "",
        range_name: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read data from a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        resolved_id = spreadsheet_id.strip() or target_id.strip()
        resolved_name = sheet_name.strip() or target_name.strip()
        resolved_range = range_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.read_sheet",
            _with_instruction_fallback(
                "sheets",
                "xem sheet",
                {
                    "spreadsheetId": resolved_id,
                    "targetId": resolved_id,
                    "sheetName": resolved_name,
                    "targetName": resolved_name,
                    "range": resolved_range,
                    "rangeName": resolved_range,
                    "sheetTab": sheet_tab.strip(),
                },
                instruction,
                resolved_id,
                resolved_name,
                resolved_range,
                sheet_tab,
            ),
            runtime,
        )

    @tool("sheets_read_range")
    def sheets_read_range_tool(
        spreadsheet_id: str = "",
        target_id: str = "",
        sheet_name: str = "",
        target_name: str = "",
        range_name: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read a specific range from Google Sheets."""
        resolved_id = spreadsheet_id.strip() or target_id.strip()
        resolved_name = sheet_name.strip() or target_name.strip()
        resolved_range = range_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.read_sheet",
            _with_instruction_fallback(
                "sheets",
                "xem vung sheet",
                {
                    "spreadsheetId": resolved_id,
                    "targetId": resolved_id,
                    "sheetName": resolved_name,
                    "targetName": resolved_name,
                    "range": resolved_range,
                    "rangeName": resolved_range,
                    "sheetTab": sheet_tab.strip(),
                },
                instruction,
                resolved_id,
                resolved_name,
                resolved_range,
                sheet_tab,
            ),
            runtime,
        )

    @tool("sheets_create_sheet")
    def sheets_create_sheet_tool(
        title: str = "",
        sheet_name: str = "",
        target_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        resolved_name = title.strip() or sheet_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.create_sheet",
            _with_instruction_fallback(
                "sheets",
                "tao sheet",
                {
                    "title": resolved_name,
                    "sheetTitle": resolved_name,
                    "sheetName": sheet_name.strip() or target_name.strip() or resolved_name,
                    "targetName": target_name.strip() or sheet_name.strip() or resolved_name,
                },
                instruction,
                resolved_name,
                sheet_name,
                target_name,
            ),
            runtime,
        )

    @tool("sheets_append_row")
    def sheets_append_row_tool(
        spreadsheet_id: str = "",
        target_id: str = "",
        sheet_name: str = "",
        target_name: str = "",
        values: list[str] | None = None,
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Append a row to Google Sheets from structured fields or a natural-language instruction."""
        resolved_id = spreadsheet_id.strip() or target_id.strip()
        resolved_name = sheet_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.append_row",
            _with_instruction_fallback(
                "sheets",
                "them dong vao sheet",
                {
                    "spreadsheetId": resolved_id,
                    "targetId": resolved_id,
                    "sheetName": resolved_name,
                    "targetName": resolved_name,
                    "sheetTab": sheet_tab.strip(),
                    "values": values or [],
                },
                instruction,
                resolved_id,
                resolved_name,
                sheet_tab,
                values or [],
            ),
            runtime,
        )

    @tool("sheets_update_cell")
    def sheets_update_cell_tool(
        spreadsheet_id: str = "",
        target_id: str = "",
        sheet_name: str = "",
        target_name: str = "",
        cell: str = "",
        value: str = "",
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Update a Google Sheets cell from structured fields or a natural-language instruction."""
        resolved_id = spreadsheet_id.strip() or target_id.strip()
        resolved_name = sheet_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.update_cell",
            _with_instruction_fallback(
                "sheets",
                "cap nhat sheet",
                {
                    "spreadsheetId": resolved_id,
                    "targetId": resolved_id,
                    "sheetName": resolved_name,
                    "targetName": resolved_name,
                    "sheetTab": sheet_tab.strip(),
                    "cell": cell.strip(),
                    "range": cell.strip(),
                    "rangeName": cell.strip(),
                    "value": value.strip(),
                },
                instruction,
                resolved_id,
                resolved_name,
                sheet_tab,
                cell,
                value,
            ),
            runtime,
        )

    @tool("sheets_update_range")
    def sheets_update_range_tool(
        spreadsheet_id: str = "",
        target_id: str = "",
        sheet_name: str = "",
        target_name: str = "",
        range_name: str = "",
        content: str = "",
        values: list[list[str]] | None = None,
        sheet_tab: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Update a range in Google Sheets."""
        spreadsheet = spreadsheet_id.strip() or target_id.strip()
        sheet_label = sheet_name.strip() or target_name.strip()
        payload: dict[str, Any] = {
            "spreadsheetId": spreadsheet,
            "targetId": spreadsheet,
            "sheetName": sheet_label,
            "targetName": sheet_label,
            "range": range_name.strip(),
            "rangeName": range_name.strip(),
            "sheetTab": sheet_tab.strip(),
            "content": content.strip(),
        }
        if values is not None:
            payload["values"] = values
        return _run_gateway_tool(
            tool_gateway,
            "sheets.update_range",
            _with_instruction_fallback(
                "sheets",
                "cap nhat vung sheet",
                payload,
                instruction,
                spreadsheet,
                sheet_label,
                range_name,
                sheet_tab,
                content,
                values if values is not None else [],
            ),
            runtime,
        )

    @tool("sheets_delete_sheet")
    def sheets_delete_sheet_tool(
        spreadsheet_id: str = "",
        sheet_name: str = "",
        target_id: str = "",
        target_name: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Delete a Google Sheets spreadsheet from structured fields or a natural-language instruction."""
        resolved_id = spreadsheet_id.strip() or target_id.strip()
        resolved_name = sheet_name.strip() or target_name.strip()
        return _run_gateway_tool(
            tool_gateway,
            "sheets.delete_sheet",
            _with_instruction_fallback(
                "sheets",
                "xoa sheet",
                {
                    "spreadsheetId": resolved_id,
                    "targetId": resolved_id,
                    "sheetName": resolved_name,
                    "targetName": resolved_name,
                },
                instruction,
                resolved_id,
                resolved_name,
            ),
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
