from __future__ import annotations

import unittest
from dataclasses import dataclass

from agent.models import MiaContext
from agent.skills.google import get_google_tools


@dataclass
class _DummyGatewayResult:
    text: str


class _DummyGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def run_tool(self, tool_name: str, args: dict[str, object], _context: MiaContext) -> _DummyGatewayResult:
        self.calls.append((tool_name, dict(args)))
        return _DummyGatewayResult(text="ok")


class _DummyRuntime:
    def __init__(self) -> None:
        self.context = MiaContext(
            chat_id="chat-1",
            user_id="user-1",
            timezone="Asia/Ho_Chi_Minh",
            request_id="req-1",
        )


class GoogleToolStructuredPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = _DummyGateway()
        self.runtime = _DummyRuntime()
        self.tools = {tool.name: tool for tool in get_google_tools(self.gateway)}

    def test_calendar_find_event_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["calendar_find_event"].func(  # type: ignore[union-attr]
            query="họp khách",
            date_from="2026-06-29T00:00:00+07:00",
            date_to="2026-06-30T00:00:00+07:00",
            calendar_id="primary",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "calendar.find_event")
        self.assertEqual(args["query"], "họp khách")
        self.assertNotIn("instruction", args)

    def test_calendar_find_free_slot_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["calendar_find_free_slot"].func(  # type: ignore[union-attr]
            date="2026-07-02",
            start_at="2026-07-02T13:00:00+07:00",
            end_at="2026-07-02T18:00:00+07:00",
            duration_minutes=45,
            calendar_id="primary",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "calendar.find_free_slot")
        self.assertEqual(args["date"], "2026-07-02")
        self.assertEqual(args["startAt"], "2026-07-02T13:00:00+07:00")
        self.assertEqual(args["endAt"], "2026-07-02T18:00:00+07:00")
        self.assertEqual(args["durationMinutes"], 45)
        self.assertEqual(args["calendarId"], "primary")
        self.assertNotIn("instruction", args)

    def test_calendar_reschedule_event_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["calendar_reschedule_event"].func(  # type: ignore[union-attr]
            event_id="evt-1",
            query="họp khách",
            start_at="2026-07-03T09:00:00+07:00",
            end_at="2026-07-03T10:00:00+07:00",
            timezone="Asia/Ho_Chi_Minh",
            calendar_id="primary",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "calendar.reschedule_event")
        self.assertEqual(args["eventId"], "evt-1")
        self.assertEqual(args["query"], "họp khách")
        self.assertEqual(args["startAt"], "2026-07-03T09:00:00+07:00")
        self.assertEqual(args["endAt"], "2026-07-03T10:00:00+07:00")
        self.assertEqual(args["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(args["calendarId"], "primary")
        self.assertNotIn("instruction", args)

    def test_drive_create_file_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_create_file"].func(  # type: ignore[union-attr]
            name="note.md",
            target_name="note.md",
            content="# hello",
            mime_type="text/markdown",
            parent_id="folder-1",
            target_folder_id="folder-1",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.create_file")
        self.assertEqual(args["fileName"], "note.md")
        self.assertEqual(args["targetName"], "note.md")
        self.assertEqual(args["content"], "# hello")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_drive_create_folder_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_create_folder"].func(  # type: ignore[union-attr]
            name="Khach hang",
            target_name="Khach hang",
            parent_id="folder-1",
            target_folder_id="folder-1",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.create_folder")
        self.assertEqual(args["name"], "Khach hang")
        self.assertEqual(args["folderName"], "Khach hang")
        self.assertEqual(args["targetName"], "Khach hang")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertEqual(args["parentId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_drive_upload_file_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_upload_file"].func(  # type: ignore[union-attr]
            file_id="tg-file-1",
            file_name="bao-cao.pdf",
            target_name="bao-cao.pdf",
            mime_type="application/pdf",
            folder_id="folder-123",
            target_folder_id="folder-123",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.upload_file")
        self.assertEqual(args["telegramFileId"], "tg-file-1")
        self.assertEqual(args["fileName"], "bao-cao.pdf")
        self.assertEqual(args["targetName"], "bao-cao.pdf")
        self.assertEqual(args["folderId"], "folder-123")
        self.assertEqual(args["targetFolderId"], "folder-123")
        self.assertNotIn("instruction", args)

    def test_drive_delete_folder_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_delete_folder"].func(  # type: ignore[union-attr]
            folder_id="folder-123",
            target_id="folder-123",
            folder_name="Khach hang",
            target_name="Khach hang",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.delete_folder")
        self.assertEqual(args["folderId"], "folder-123")
        self.assertEqual(args["targetId"], "folder-123")
        self.assertEqual(args["folderName"], "Khach hang")
        self.assertEqual(args["targetName"], "Khach hang")
        self.assertNotIn("instruction", args)

    def test_drive_search_file_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_search_file"].func(  # type: ignore[union-attr]
            query="hợp đồng",
            mime_type="application/pdf",
            folder_id="folder-1",
            limit=4,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.search_file")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["fileName"], "hợp đồng")
        self.assertEqual(args["mimeType"], "application/pdf")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_drive_share_file_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_share_file"].func(  # type: ignore[union-attr]
            target_name="briefing.pdf",
            email="user@example.com",
            role="writer",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.share_file")
        self.assertEqual(args["fileName"], "briefing.pdf")
        self.assertEqual(args["targetName"], "briefing.pdf")
        self.assertEqual(args["email"], "user@example.com")
        self.assertEqual(args["role"], "writer")
        self.assertNotIn("instruction", args)

    def test_drive_copy_file_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["drive_copy_file"].func(  # type: ignore[union-attr]
            target_name="template.md",
            new_name="template-copy.md",
            parent_id="folder-1",
            target_folder_name="Folder A",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.copy_file")
        self.assertEqual(args["fileName"], "template.md")
        self.assertEqual(args["targetName"], "template.md")
        self.assertEqual(args["newName"], "template-copy.md")
        self.assertEqual(args["parentId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertEqual(args["targetFolderName"], "Folder A")
        self.assertNotIn("instruction", args)

    def test_gmail_search_email_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_search_email"].func(  # type: ignore[union-attr]
            query="hợp đồng",
            sender="ceo@example.com",
            subject="Q3",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.search_email")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertNotIn("instruction", args)

    def test_gmail_read_email_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_read_email"].func(  # type: ignore[union-attr]
            message_id="msg-1",
            sender="boss@example.com",
            subject="Đơn hàng",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.read_email")
        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["sender"], "boss@example.com")
        self.assertEqual(args["subject"], "Đơn hàng")
        self.assertNotIn("instruction", args)

    def test_gmail_reply_email_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_reply_email"].func(  # type: ignore[union-attr]
            message_id="msg-1",
            search_query="from:boss@example.com subject:Đơn hàng",
            body="Đã nhận, em xử lý ngay.",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.reply_email")
        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["searchQuery"], "from:boss@example.com subject:Đơn hàng")
        self.assertEqual(args["body"], "Đã nhận, em xử lý ngay.")
        self.assertNotIn("instruction", args)

    def test_gmail_search_by_sender_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_search_by_sender"].func(  # type: ignore[union-attr]
            sender="ceo@example.com",
            query="hợp đồng",
            subject="Q3",
            limit=4,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.search_by_sender")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["subject"], "Q3")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_gmail_mark_read_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_mark_read"].func(  # type: ignore[union-attr]
            message_id="msg-1",
            query="hợp đồng",
            sender="ceo@example.com",
            subject="Q3",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.mark_read")
        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["subject"], "Q3")
        self.assertNotIn("instruction", args)

    def test_gmail_archive_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["gmail_archive"].func(  # type: ignore[union-attr]
            message_id="msg-1",
            query="hợp đồng",
            sender="ceo@example.com",
            subject="Q3",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "gmail.archive")
        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["subject"], "Q3")
        self.assertNotIn("instruction", args)

    def test_docs_search_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_search_doc"].func(  # type: ignore[union-attr]
            query="Project Plan",
            folder_id="folder-1",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.search_doc")
        self.assertEqual(args["query"], "Project Plan")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_docs_search_doc_accepts_target_name_only(self) -> None:
        self.tools["docs_search_doc"].func(  # type: ignore[union-attr]
            query="",
            target_name="Project Plan",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.search_doc")
        self.assertEqual(args["query"], "Project Plan")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_sheets_search_sheet_accepts_target_name_only(self) -> None:
        self.tools["sheets_search_sheet"].func(  # type: ignore[union-attr]
            query="",
            target_name="Báo cáo",
            folder_id="folder-2",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.search_sheet")
        self.assertEqual(args["query"], "Báo cáo")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["folderId"], "folder-2")
        self.assertNotIn("instruction", args)

    def test_docs_append_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_append_doc"].func(  # type: ignore[union-attr]
            document_id="doc-1",
            doc_name="Project Plan",
            content="thêm nội dung mới",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.append_doc")
        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["content"], "thêm nội dung mới")
        self.assertNotIn("instruction", args)

    def test_docs_update_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_update_doc"].func(  # type: ignore[union-attr]
            document_id="doc-1",
            doc_name="Project Plan",
            content="nội dung mới",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.update_doc")
        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["content"], "nội dung mới")
        self.assertNotIn("instruction", args)

    def test_docs_read_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_read_doc"].func(  # type: ignore[union-attr]
            target_id="doc-1",
            target_name="Project Plan",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.read_doc")
        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_sheets_read_sheet_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_read_sheet"].func(  # type: ignore[union-attr]
            target_id="sheet-1",
            target_name="Chi tiêu",
            range_name="A1:C10",
            sheet_tab="2026",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.read_sheet")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Chi tiêu")
        self.assertEqual(args["targetName"], "Chi tiêu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertEqual(args["rangeName"], "A1:C10")
        self.assertEqual(args["sheetTab"], "2026")
        self.assertNotIn("instruction", args)

    def test_docs_create_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_create_doc"].func(  # type: ignore[union-attr]
            target_name="Project Plan",
            content="nội dung",
            target_folder_id="folder-1",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.create_doc")
        self.assertEqual(args["title"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_docs_delete_doc_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["docs_delete_doc"].func(  # type: ignore[union-attr]
            target_id="doc-1",
            target_name="Project Plan",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "docs.delete_doc")
        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_google_tool_keeps_instruction_fallback_when_no_structured_args(self) -> None:
        self.tools["drive_create_folder"].func(runtime=self.runtime)  # type: ignore[union-attr]

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "drive.create_folder")
        self.assertIn("instruction", args)
        self.assertTrue(str(args["instruction"]).strip())

    def test_sheets_read_range_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_read_range"].func(  # type: ignore[union-attr]
            target_id="sheet-1",
            target_name="Chi tieu",
            range_name="A1:C10",
            sheet_tab="Data",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.read_sheet")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Chi tieu")
        self.assertEqual(args["targetName"], "Chi tieu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertEqual(args["rangeName"], "A1:C10")
        self.assertEqual(args["sheetTab"], "Data")
        self.assertNotIn("instruction", args)

    def test_sheets_update_range_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_update_range"].func(  # type: ignore[union-attr]
            spreadsheet_id="sheet-1",
            target_name="Báo cáo",
            range_name="A1:C3",
            content="1,2,3",
            values=[["1", "2", "3"]],
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.update_range")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["range"], "A1:C3")
        self.assertEqual(args["rangeName"], "A1:C3")
        self.assertEqual(args["values"], [["1", "2", "3"]])
        self.assertNotIn("instruction", args)

    def test_sheets_create_sheet_accepts_target_name_only(self) -> None:
        self.tools["sheets_create_sheet"].func(  # type: ignore[union-attr]
            target_name="Báo cáo",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.create_sheet")
        self.assertEqual(args["title"], "Báo cáo")
        self.assertEqual(args["sheetTitle"], "Báo cáo")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertNotIn("instruction", args)

    def test_sheets_append_row_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_append_row"].func(  # type: ignore[union-attr]
            target_id="sheet-1",
            target_name="Báo cáo",
            sheet_tab="Data",
            values=["1", "2", "3"],
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.append_row")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["sheetTab"], "Data")
        self.assertEqual(args["values"], ["1", "2", "3"])
        self.assertNotIn("instruction", args)

    def test_sheets_update_cell_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_update_cell"].func(  # type: ignore[union-attr]
            target_id="sheet-1",
            target_name="Báo cáo",
            cell="B2",
            value="42",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.update_cell")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["cell"], "B2")
        self.assertEqual(args["range"], "B2")
        self.assertEqual(args["rangeName"], "B2")
        self.assertEqual(args["value"], "42")
        self.assertNotIn("instruction", args)

    def test_sheets_delete_sheet_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["sheets_delete_sheet"].func(  # type: ignore[union-attr]
            target_id="sheet-1",
            target_name="Báo cáo",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "sheets.delete_sheet")
        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertNotIn("instruction", args)
