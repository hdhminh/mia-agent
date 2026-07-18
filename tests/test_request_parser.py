from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Force Vietnamese locale for tests that assert Vietnamese parse output
os.environ["MIA_LOCALE"] = "vi"



ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.brain.planner import build_direct_tool_args
from agent.brain.router import route_request


class TestRequestParserUrlInstructions(unittest.TestCase):
    def test_summarize_url_instruction_drops_url(self) -> None:
        url = "https://example.com/article-2"
        args = build_direct_tool_args("summarize_url", f"tóm tắt link này {url}", {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "tóm tắt link này")
        self.assertEqual(args["text"], "tóm tắt link này")
        self.assertEqual(args["prompt"], "tóm tắt link này")

    def test_ask_url_instruction_keeps_question_without_url(self) -> None:
        url = "https://example.com/article-3"
        args = build_direct_tool_args("ask_url", f"{url} link này nói gì về học phí?", {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "link này nói gì về học phí?")
        self.assertEqual(args["question"], "link này nói gì về học phí?")
        self.assertEqual(args["prompt"], "link này nói gì về học phí?")

    def test_ask_url_with_only_url_falls_back_to_generic_question(self) -> None:
        url = "https://example.com/article-4"
        args = build_direct_tool_args("ask_url", url, {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "hỏi tiếp link này")
        self.assertEqual(args["question"], "hỏi tiếp link này")

    def test_read_url_preserves_fetch_strategy(self) -> None:
        url = "https://example.com/article-5"
        args = build_direct_tool_args(
            "read_url",
            f"đọc link này {url}",
            {"url": url, "fetchStrategy": "browser", "maxChars": 1200},
        )

        self.assertEqual(args["url"], url)
        self.assertEqual(args["fetchStrategy"], "browser")
        self.assertEqual(args["max_chars"], 1200)


class TestRequestParserCurrentTime(unittest.TestCase):
    def test_current_time_question_routes_to_time_now(self) -> None:
        route = route_request("hôm nay là thứ mấy z")

        self.assertTrue(route.use_direct)
        self.assertEqual(route.route_type, "direct_deterministic")
        self.assertEqual(route.hint_tool, "time_now")

    def test_time_now_direct_args_are_empty(self) -> None:
        args = build_direct_tool_args("time_now", "hôm nay là thứ mấy z")

        self.assertEqual(args, {})


class TestRequestParserGitHubReadOnlyExpansion(unittest.TestCase):
    def test_github_release_url_routes_to_get_release(self) -> None:
        url = "https://github.com/octocat/hello-world/releases"
        route = route_request(f"xem release mới nhất {url}")

        self.assertTrue(route.use_direct)
        self.assertEqual(route.route_type, "direct_deterministic")
        self.assertEqual(route.hint_tool, "github_get_release")

        args = build_direct_tool_args(
            "github_get_release",
            f"xem release mới nhất {url}",
            {"repoUrl": "https://github.com/octocat/hello-world"},
        )
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["releaseId"], "latest")

    def test_github_pull_request_url_routes_to_get_pull_request(self) -> None:
        url = "https://github.com/octocat/hello-world/pull/42"
        route = route_request(f"xem PR #42 {url}")

        self.assertTrue(route.use_direct)
        self.assertEqual(route.route_type, "direct_deterministic")
        self.assertEqual(route.hint_tool, "github_get_pull_request")

        args = build_direct_tool_args("github_get_pull_request", f"xem PR #42 {url}")
        self.assertEqual(args["number"], "42")

    def test_github_issue_url_routes_to_get_issue(self) -> None:
        url = "https://github.com/octocat/hello-world/issues/7"
        route = route_request(f"xem issue #7 {url}")

        self.assertTrue(route.use_direct)
        self.assertEqual(route.route_type, "direct_deterministic")
        self.assertEqual(route.hint_tool, "github_get_issue")

        args = build_direct_tool_args("github_get_issue", f"xem issue #7 {url}")
        self.assertEqual(args["number"], "7")

    def test_github_create_issue_routes_to_write_tool(self) -> None:
        route = route_request("tạo issue test trong repo octocat/hello-world tiêu đề Smoke")

        self.assertEqual(route.route_type, "agentic_domain")
        self.assertEqual(route.domain, "github")
        self.assertEqual(route.hint_tool, "github_create_issue")


class TestRequestParserGitHubStructuredArgs(unittest.TestCase):
    def test_github_list_releases_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "github_list_releases",
            "xem releases repo octocat/hello-world",
            {"repo": "octocat/hello-world", "limit": 5},
        )

        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["limit"], 5)
        self.assertNotIn("instruction", args)

    def test_github_get_release_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "github_get_release",
            "xem release latest repo octocat/hello-world",
            {"repo": "octocat/hello-world", "releaseId": "latest"},
        )

        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["releaseId"], "latest")
        self.assertNotIn("instruction", args)

    def test_github_list_pull_requests_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "github_list_pull_requests",
            "xem PR open repo octocat/hello-world",
            {"repo": "octocat/hello-world", "state": "open", "limit": 10},
        )

        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["state"], "open")
        self.assertEqual(args["limit"], 10)
        self.assertNotIn("instruction", args)

    def test_github_get_issue_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "github_get_issue",
            "xem issue #7 repo octocat/hello-world",
            {"repo": "octocat/hello-world", "number": "7"},
        )

        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["number"], "7")
        self.assertNotIn("instruction", args)

    def test_github_search_code_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "github_search_code",
            "tìm code repo octocat/hello-world query:workflow",
            {"repo": "octocat/hello-world", "query": "workflow"},
        )

        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertIn("workflow", args["query"])
        self.assertIn("repo:octocat/hello-world", args["query"])
        self.assertNotIn("instruction", args)


class TestRequestParserStructuredGoogleArgs(unittest.TestCase):
    def test_docs_search_doc_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "docs_search_doc",
            "tìm doc Project Plan",
            {
                "targetName": "Project Plan",
                "folderId": "folder-1",
                "limit": 4,
            },
        )

        self.assertEqual(args["query"], "Project Plan")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_sheets_search_sheet_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "sheets_search_sheet",
            "tìm sheet Báo cáo",
            {
                "targetName": "Báo cáo",
                "folderId": "folder-2",
                "limit": 4,
            },
        )

        self.assertEqual(args["query"], "Báo cáo")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["folderId"], "folder-2")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_docs_read_doc_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args("docs_read_doc", "đọc doc Project Plan")

        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["fileName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_docs_read_doc_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "docs_read_doc",
            "đọc doc Project Plan",
            {
                "targetId": "doc-1",
                "targetName": "Project Plan",
                "maxChars": 1200,
            },
        )

        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["maxChars"], 1200)
        self.assertNotIn("instruction", args)

    def test_docs_update_doc_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "docs_update_doc",
            "cập nhật doc Project Plan với nội dung mới",
            {
                "targetId": "doc-1",
                "targetName": "Project Plan",
                "content": "nội dung mới",
            },
        )

        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["content"], "nội dung mới")
        self.assertNotIn("instruction", args)

    def test_docs_create_doc_direct_args_keep_structured_target_aliases(self) -> None:
        args = build_direct_tool_args(
            "docs_create_doc",
            "tạo doc Project Plan trong folder Khách hàng",
            {
                "targetName": "Project Plan",
                "targetFolderId": "folder-1",
                "content": "nội dung",
            },
        )

        self.assertEqual(args["title"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_docs_append_doc_direct_args_keep_structured_target_aliases(self) -> None:
        args = build_direct_tool_args(
            "docs_append_doc",
            "thêm nội dung vào doc Project Plan",
            {
                "targetId": "doc-1",
                "targetName": "Project Plan",
                "content": "nội dung mới",
            },
        )

        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_docs_delete_doc_direct_args_keep_structured_target_aliases(self) -> None:
        args = build_direct_tool_args(
            "docs_delete_doc",
            "xóa doc Project Plan",
            {
                "targetId": "doc-1",
                "targetName": "Project Plan",
            },
        )

        self.assertEqual(args["docId"], "doc-1")
        self.assertEqual(args["targetId"], "doc-1")
        self.assertEqual(args["docName"], "Project Plan")
        self.assertEqual(args["targetName"], "Project Plan")
        self.assertNotIn("instruction", args)

    def test_sheets_read_sheet_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args("sheets_read_sheet", "đọc sheet Chi tiêu A1:C10")

        self.assertEqual(args["sheetName"], "Chi tiêu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertNotIn("instruction", args)

    def test_sheets_read_sheet_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "sheets_read_sheet",
            "đọc sheet Chi tiêu A1:C10",
            {
                "targetId": "sheet-1",
                "targetName": "Chi tiêu",
                "rangeName": "A1:C10",
                "sheetTab": "2026",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Chi tiêu")
        self.assertEqual(args["targetName"], "Chi tiêu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertEqual(args["rangeName"], "A1:C10")
        self.assertEqual(args["sheetTab"], "2026")
        self.assertNotIn("instruction", args)

    def test_sheets_read_range_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args("sheets_read_range", "xem vùng sheet Chi tiêu A1:C10")

        self.assertEqual(args["sheetName"], "Chi tiêu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertNotIn("instruction", args)

    def test_sheets_read_range_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "sheets_read_range",
            "xem vùng sheet Chi tiêu A1:C10",
            {
                "targetId": "sheet-1",
                "targetName": "Chi tiêu",
                "rangeName": "A1:C10",
                "sheetTab": "2026",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Chi tiêu")
        self.assertEqual(args["targetName"], "Chi tiêu")
        self.assertEqual(args["range"], "A1:C10")
        self.assertEqual(args["rangeName"], "A1:C10")
        self.assertEqual(args["sheetTab"], "2026")
        self.assertNotIn("instruction", args)

    def test_sheets_update_range_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "sheets_update_range",
            "cập nhật vùng sheet Báo cáo A1:C3",
            {
                "spreadsheetId": "sheet-1",
                "sheetName": "Báo cáo",
                "range": "A1:C3",
                "content": "1,2,3",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["range"], "A1:C3")
        self.assertEqual(args["rangeName"], "A1:C3")
        self.assertEqual(args["content"], "1,2,3")
        self.assertNotIn("instruction", args)

    def test_sheets_create_sheet_direct_args_preserve_target_name(self) -> None:
        args = build_direct_tool_args(
            "sheets_create_sheet",
            "tạo sheet Báo cáo",
            {"targetName": "Báo cáo"},
        )

        self.assertEqual(args["title"], "Báo cáo")
        self.assertEqual(args["sheetTitle"], "Báo cáo")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertNotIn("instruction", args)

    def test_sheets_update_cell_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "sheets_update_cell",
            "cập nhật sheet Báo cáo ô B2",
            {
                "targetId": "sheet-1",
                "targetName": "Báo cáo",
                "rangeName": "B2",
                "value": "42",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["range"], "B2")
        self.assertEqual(args["rangeName"], "B2")
        self.assertEqual(args["value"], "42")
        self.assertNotIn("instruction", args)

    def test_sheets_append_row_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "sheets_append_row",
            "thêm dòng vào sheet Báo cáo",
            {
                "targetId": "sheet-1",
                "targetName": "Báo cáo",
                "sheetTab": "Data",
                "values": [["1", "2", "3"]],
                "rowData": "1,2,3",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["sheetTab"], "Data")
        self.assertEqual(args["values"], [["1", "2", "3"]])
        self.assertEqual(args["rowData"], "1,2,3")
        self.assertEqual(args["content"], "1,2,3")
        self.assertNotIn("instruction", args)

    def test_sheets_delete_sheet_direct_args_preserve_structured_aliases(self) -> None:
        args = build_direct_tool_args(
            "sheets_delete_sheet",
            "xóa sheet Báo cáo",
            {
                "targetId": "sheet-1",
                "targetName": "Báo cáo",
            },
        )

        self.assertEqual(args["spreadsheetId"], "sheet-1")
        self.assertEqual(args["targetId"], "sheet-1")
        self.assertEqual(args["sheetName"], "Báo cáo")
        self.assertEqual(args["targetName"], "Báo cáo")
        self.assertEqual(args["fileName"], "Báo cáo")
        self.assertNotIn("instruction", args)

    def test_gmail_read_email_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "gmail_read_email",
            "đọc email đơn hàng",
            {
                "messageId": "msg-1",
                "sender": "boss@example.com",
                "subject": "Đơn hàng",
            },
        )

        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["sender"], "boss@example.com")
        self.assertEqual(args["subject"], "Đơn hàng")
        self.assertNotIn("instruction", args)

    def test_gmail_reply_email_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "gmail_reply_email",
            "trả lời email đơn hàng",
            {
                "messageId": "msg-1",
                "searchQuery": "from:boss@example.com subject:Đơn hàng",
                "body": "Đã nhận, em xử lý ngay.",
            },
        )

        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["searchQuery"], "from:boss@example.com subject:Đơn hàng")
        self.assertEqual(args["body"], "Đã nhận, em xử lý ngay.")
        self.assertNotIn("instruction", args)

    def test_drive_upload_file_uses_structured_metadata_without_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_upload_file",
            "upload file này vào drive",
            {
                "fileId": "tg-file-1",
                "fileName": "bao-cao.pdf",
                "targetName": "bao-cao.pdf",
                "mimeType": "application/pdf",
                "folderId": "folder-123",
                "targetFolderId": "folder-123",
                "hasAttachment": True,
            },
        )

        self.assertEqual(args["telegramFileId"], "tg-file-1")
        self.assertEqual(args["fileName"], "bao-cao.pdf")
        self.assertEqual(args["targetName"], "bao-cao.pdf")
        self.assertEqual(args["folderId"], "folder-123")
        self.assertEqual(args["targetFolderId"], "folder-123")
        self.assertNotIn("instruction", args)

    def test_drive_search_file_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "drive_search_file",
            "tìm file hợp đồng",
            {
                "query": "hợp đồng",
                "mimeType": "application/pdf",
                "folderId": "folder-1",
                "limit": 4,
            },
        )

        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["fileName"], "hợp đồng")
        self.assertEqual(args["mimeType"], "application/pdf")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_drive_create_folder_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_create_folder",
            "tạo folder Khách hàng",
            {
                "name": "Khách hàng",
                "parentId": "folder-1",
                "targetName": "Khách hàng",
                "targetFolderId": "folder-1",
            },
        )

        self.assertEqual(args["name"], "Khách hàng")
        self.assertEqual(args["folderName"], "Khách hàng")
        self.assertEqual(args["targetName"], "Khách hàng")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_drive_create_file_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_create_file",
            "tạo file note.md",
            {
                "name": "note.md",
                "content": "# hello",
                "mimeType": "text/markdown",
                "parentId": "folder-1",
                "targetName": "note.md",
                "targetFolderId": "folder-1",
            },
        )

        self.assertEqual(args["name"], "note.md")
        self.assertEqual(args["fileName"], "note.md")
        self.assertEqual(args["targetName"], "note.md")
        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertNotIn("instruction", args)

    def test_drive_delete_folder_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_delete_folder",
            "xóa folder Khách hàng",
            {
                "folderId": "folder-1",
                "folderName": "Khách hàng",
                "targetId": "folder-1",
                "targetName": "Khách hàng",
            },
        )

        self.assertEqual(args["folderId"], "folder-1")
        self.assertEqual(args["targetId"], "folder-1")
        self.assertEqual(args["folderName"], "Khách hàng")
        self.assertEqual(args["targetName"], "Khách hàng")
        self.assertNotIn("instruction", args)

    def test_drive_share_file_direct_args_keep_target_name_without_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_share_file",
            "chia sẻ file briefing",
            {
                "targetName": "briefing.pdf",
                "email": "user@example.com",
                "role": "writer",
            },
        )

        self.assertEqual(args["fileName"], "briefing.pdf")
        self.assertEqual(args["targetName"], "briefing.pdf")
        self.assertEqual(args["email"], "user@example.com")
        self.assertEqual(args["role"], "writer")
        self.assertNotIn("instruction", args)

    def test_drive_copy_file_direct_args_keep_target_folder_name_without_instruction(self) -> None:
        args = build_direct_tool_args(
            "drive_copy_file",
            "copy file template",
            {
                "targetName": "template.md",
                "newName": "template-copy.md",
                "parentId": "folder-1",
                "targetFolderName": "Folder A",
            },
        )

        self.assertEqual(args["fileName"], "template.md")
        self.assertEqual(args["targetName"], "template.md")
        self.assertEqual(args["newName"], "template-copy.md")
        self.assertEqual(args["targetFolderId"], "folder-1")
        self.assertEqual(args["targetFolderName"], "Folder A")
        self.assertNotIn("instruction", args)

    def test_calendar_create_event_uses_structured_metadata_without_instruction(self) -> None:
        args = build_direct_tool_args(
            "calendar_create_event",
            "tạo lịch",
            {
                "title": "Họp team",
                "startAt": "2026-06-29T15:00:00+07:00",
                "endAt": "2026-06-29T16:00:00+07:00",
                "calendarId": "primary",
            },
        )

        self.assertEqual(args["title"], "Họp team")
        self.assertEqual(args["startAt"], "2026-06-29T15:00:00+07:00")
        self.assertEqual(args["endAt"], "2026-06-29T16:00:00+07:00")
        self.assertNotIn("instruction", args)

    def test_gmail_search_email_direct_args_do_not_need_instruction(self) -> None:
        args = build_direct_tool_args("gmail_search_email", "tìm email hợp đồng")

        self.assertEqual(args["query"], "hợp đồng")
        self.assertNotIn("instruction", args)

    def test_gmail_search_email_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "gmail_search_email",
            "tìm email hợp đồng",
            {
                "query": "hợp đồng",
                "sender": "ceo@example.com",
                "subject": "Q3",
                "limit": 4,
            },
        )

        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["subject"], "Q3")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_gmail_search_by_sender_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "gmail_search_by_sender",
            "tìm email từ ceo@example.com",
            {
                "sender": "ceo@example.com",
                "query": "hợp đồng",
                "subject": "Q3",
                "limit": 4,
            },
        )

        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["subject"], "Q3")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_gmail_mark_read_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "gmail_mark_read",
            "đánh dấu email đã đọc",
            {
                "messageId": "msg-1",
                "query": "hợp đồng",
                "sender": "ceo@example.com",
                "subject": "Q3",
            },
        )

        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["subject"], "Q3")
        self.assertNotIn("instruction", args)

    def test_gmail_archive_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "gmail_archive",
            "lưu trữ email",
            {
                "messageId": "msg-1",
                "query": "hợp đồng",
                "sender": "ceo@example.com",
                "subject": "Q3",
            },
        )

        self.assertEqual(args["messageId"], "msg-1")
        self.assertEqual(args["query"], "hợp đồng")
        self.assertEqual(args["sender"], "ceo@example.com")
        self.assertEqual(args["subject"], "Q3")
        self.assertNotIn("instruction", args)

    def test_calendar_find_event_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "calendar_find_event",
            "tìm lịch họp khách",
            {
                "query": "họp khách",
                "dateFrom": "2026-06-29T00:00:00+07:00",
                "dateTo": "2026-06-30T00:00:00+07:00",
                "calendarId": "primary",
                "limit": 4,
            },
        )

        self.assertEqual(args["query"], "họp khách")
        self.assertEqual(args["dateFrom"], "2026-06-29T00:00:00+07:00")
        self.assertEqual(args["dateTo"], "2026-06-30T00:00:00+07:00")
        self.assertEqual(args["calendarId"], "primary")
        self.assertEqual(args["limit"], 4)
        self.assertNotIn("instruction", args)

    def test_calendar_find_free_slot_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "calendar_find_free_slot",
            "tìm khung giờ rảnh chiều mai",
            {
                "date": "2026-07-02",
                "startAt": "2026-07-02T13:00:00+07:00",
                "endAt": "2026-07-02T18:00:00+07:00",
                "durationMinutes": 45,
                "calendarId": "primary",
            },
        )

        self.assertEqual(args["date"], "2026-07-02")
        self.assertEqual(args["startAt"], "2026-07-02T13:00:00+07:00")
        self.assertEqual(args["endAt"], "2026-07-02T18:00:00+07:00")
        self.assertEqual(args["durationMinutes"], 45)
        self.assertEqual(args["calendarId"], "primary")
        self.assertNotIn("instruction", args)

    def test_calendar_reschedule_event_direct_args_preserve_structured_filters(self) -> None:
        args = build_direct_tool_args(
            "calendar_reschedule_event",
            "đổi lịch họp khách",
            {
                "eventId": "evt-1",
                "query": "họp khách",
                "startAt": "2026-07-03T09:00:00+07:00",
                "endAt": "2026-07-03T10:00:00+07:00",
                "timezone": "Asia/Ho_Chi_Minh",
                "calendarId": "primary",
            },
        )

        self.assertEqual(args["eventId"], "evt-1")
        self.assertEqual(args["query"], "họp khách")
        self.assertEqual(args["startAt"], "2026-07-03T09:00:00+07:00")
        self.assertEqual(args["endAt"], "2026-07-03T10:00:00+07:00")
        self.assertEqual(args["timezone"], "Asia/Ho_Chi_Minh")
        self.assertEqual(args["calendarId"], "primary")
        self.assertNotIn("instruction", args)
