from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT_MAINTENANCE_ROOT = ROOT / "scripts" / "maintenance"
if str(SCRIPT_MAINTENANCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_MAINTENANCE_ROOT))

from workflow_validation import validate_workflow_data, validate_workflow_file


class TestWorkflowArtifacts(unittest.TestCase):
    def test_web_master_routes_to_real_workflow_id(self) -> None:
        path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))
        route_node = next(node for node in workflow["nodes"] if node.get("name") == "Route Tool")
        js_code = str(route_node["parameters"]["jsCode"])

        match = re.search(r"'web\.master':\s*'([^']+)'", js_code)
        self.assertIsNotNone(match, "web.master mapping is missing from Route Tool")
        workflow_id = match.group(1)

        self.assertNotEqual(workflow_id, "Sub-workflow: Web Master")
        self.assertGreaterEqual(len(workflow_id), 12)
        self.assertNotIn(" ", workflow_id)

    def test_web_workflow_carries_fetch_strategy(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        web_path = ROOT / "execution" / "integrations" / "web" / "workflow_sub_web_master.json"

        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))
        web = json.loads(web_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("fetchStrategy", prepare_code)

        input_node = next(node for node in web["nodes"] if node.get("name") == "Normalize Web Input")
        input_code = str(input_node["parameters"]["jsCode"])
        self.assertIn("fetchStrategy", input_code)
        self.assertIn("fetch_strategy", input_code)

        result_node = next(node for node in web["nodes"] if node.get("name") == "Normalize Web Result")
        result_code = str(result_node["parameters"]["jsCode"])
        self.assertIn("fetchStrategy", result_code)
        self.assertIn("fetch_strategy", result_code)

    def test_github_workflow_supports_new_read_only_tools(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        github_path = ROOT / "execution" / "integrations" / "github" / "workflow_sub_github_master.json"

        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))
        github = json.loads(github_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        for tool_name in (
            "github.list_releases",
            "github.get_release",
            "github.list_pull_requests",
            "github.get_pull_request",
            "github.list_issues",
            "github.get_issue",
        ):
            self.assertIn(tool_name, prepare_code)

        input_node = next(node for node in github["nodes"] if node.get("name") == "Normalize GitHub Input")
        input_code = str(input_node["parameters"]["jsCode"])
        for tool_name in (
            "github.list_releases",
            "github.get_release",
            "github.list_pull_requests",
            "github.get_pull_request",
            "github.list_issues",
            "github.get_issue",
        ):
            self.assertIn(tool_name, input_code)

        result_node = next(node for node in github["nodes"] if node.get("name") == "Normalize GitHub Result")
        result_code = str(result_node["parameters"]["jsCode"])
        for summary_label in ("releases", "release", "pull_requests", "pull_request", "issues", "issue"):
            self.assertIn(f"summaryLabel === '{summary_label}'", result_code)

    def test_gmail_send_and_draft_preserve_structured_cc_bcc(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        send_path = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_send_email.json"
        draft_path = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_draft_email.json"

        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))
        send = json.loads(send_path.read_text(encoding="utf-8"))
        draft = json.loads(draft_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        for field_name in ("cc", "bcc", "toEmail", "subject", "body"):
            self.assertIn(field_name, prepare_code)

        send_prepare = next(node for node in send["nodes"] if node.get("name") == "Parse Gui Email")
        send_prepare_code = str(send_prepare["parameters"]["jsCode"])
        self.assertIn("structuredCc", send_prepare_code)
        self.assertIn("structuredBcc", send_prepare_code)

        send_node = next(node for node in send["nodes"] if node.get("name") == "Gmail Send")
        send_node_json = json.dumps(send_node, ensure_ascii=False)
        self.assertIn("ccList", send_node_json)
        self.assertIn("bccList", send_node_json)

        send_draft_node = next(node for node in send["nodes"] if node.get("name") == "Gmail Create And Send Draft")
        send_draft_json = json.dumps(send_draft_node, ensure_ascii=False)
        self.assertIn("ccList", send_draft_json)
        self.assertIn("bccList", send_draft_json)

        draft_prepare = next(node for node in draft["nodes"] if node.get("name") == "Parse Draft Email")
        draft_prepare_code = str(draft_prepare["parameters"]["jsCode"])
        self.assertIn("structuredCc", draft_prepare_code)
        self.assertIn("structuredBcc", draft_prepare_code)

        draft_node = next(node for node in draft["nodes"] if node.get("name") == "Gmail Draft")
        draft_node_json = json.dumps(draft_node, ensure_ascii=False)
        self.assertIn("ccList", draft_node_json)
        self.assertIn("bccList", draft_node_json)

    def test_drive_gateway_preserves_structured_fields_for_legacy_actions(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        expected_fields = {
            "drive.get_file_info": ("fileId", "targetId", "fileName", "targetName"),
            "drive.create_folder": ("name", "folderName", "targetName", "folderId", "targetFolderId", "parentId"),
            "drive.download_file": ("fileId", "targetId", "fileName", "targetName"),
            "drive.share_file": ("fileId", "targetId", "fileName", "targetName", "email", "role"),
            "drive.move_file": (
                "fileId",
                "targetId",
                "fileName",
                "targetFolderId",
                "folderId",
                "targetFolderName",
                "folderName",
            ),
            "drive.rename_file": ("fileId", "targetId", "fileName", "targetName", "newName"),
            "drive.copy_file": (
                "fileId",
                "targetId",
                "fileName",
                "targetName",
                "newName",
                "parentId",
                "targetFolderId",
                "targetFolderName",
                "folderName",
            ),
            "drive.delete_file": ("fileId", "targetId", "fileName", "targetName"),
            "drive.delete_folder": ("folderId", "targetId", "folderName", "targetName"),
            "drive.export_file": ("fileId", "targetId", "fileName", "targetName", "mimeType", "format"),
        }

        for tool_name, field_names in expected_fields.items():
            start = prepare_code.index(f"'{tool_name}':")
            end = prepare_code.find("\n  '", start + 1)
            block = prepare_code[start:] if end == -1 else prepare_code[start:end]
            for field_name in field_names:
                self.assertIn(field_name, block, f"{tool_name} should preserve {field_name}")

    def test_drive_create_and_upload_gateway_preserve_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        expected_fields = {
            "drive.create_file": ("fileName", "name", "targetName", "content", "mimeType", "folderId", "targetFolderId", "parentId"),
            "drive.upload_file": ("telegramFileId", "fileId", "fileName", "targetName", "mimeType", "folderId", "targetFolderId"),
        }

        for tool_name, field_names in expected_fields.items():
            start = prepare_code.index(f"'{tool_name}':")
            end = prepare_code.find("\n  '", start + 1)
            block = prepare_code[start:] if end == -1 else prepare_code[start:end]
            for field_name in field_names:
                self.assertIn(field_name, block, f"{tool_name} should preserve {field_name}")

    def test_drive_leaf_workflows_have_names_and_validate(self) -> None:
        workflows = {
            "create_file": ("workflow_sub_google_drive_create_file.json", "Sub-workflow: Google Drive - Create File"),
            "create_folder": ("workflow_sub_google_drive_create_folder.json", "Sub-workflow: Google Drive - Create Folder"),
            "download_file": ("workflow_sub_google_drive_download_file.json", "Sub-workflow: Google Drive - Download File"),
            "export_file": ("workflow_sub_google_drive_export_file.json", "Sub-workflow: Google Drive - Export File"),
            "get_file_info": ("workflow_sub_google_drive_get_file_info.json", "Sub-workflow: Google Drive - Get File Info"),
            "help": ("workflow_sub_google_drive_help.json", "Sub-workflow: Google Drive - Help"),
            "list_files": ("workflow_sub_google_drive_list_files.json", "Sub-workflow: Google Drive - List Files"),
            "search_file": ("workflow_sub_google_drive_search_file.json", "Sub-workflow: Google Drive - Search File"),
            "upload_file": ("workflow_sub_google_drive_upload_file.json", "Sub-workflow: Google Drive - Upload File"),
        }

        for _, (filename, expected_name) in workflows.items():
            path = ROOT / "execution" / "integrations" / "google" / "drive" / filename
            workflow = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(workflow.get("name"), expected_name)
            self.assertEqual(validate_workflow_file(path), [])

    def test_drive_leaf_workflows_preserve_structured_target_aliases(self) -> None:
        expected = {
            "workflow_sub_google_drive_create_folder.json": ("targetName", "targetFolderId"),
            "workflow_sub_google_drive_create_file.json": ("targetName", "targetFolderId"),
            "workflow_sub_google_drive_upload_file.json": ("targetName", "targetFolderId"),
        }

        for filename, field_names in expected.items():
            path = ROOT / "execution" / "integrations" / "google" / "drive" / filename
            workflow = json.loads(path.read_text(encoding="utf-8"))
            prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
            js_code = str(prepare_node["parameters"]["jsCode"])
            for field_name in field_names:
                self.assertIn(field_name, js_code, f"{filename} should preserve {field_name}")

    def test_docs_and_sheets_gateway_preserve_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        expected_fields = {
            "docs.search_doc": ("query", "docName", "targetName", "folderId", "limit"),
            "docs.read_doc": (
                "docId",
                "documentId",
                "fileId",
                "targetId",
                "docName",
                "targetName",
                "fileName",
                "title",
                "maxChars",
            ),
            "docs.create_doc": (
                "title",
                "docTitle",
                "fileName",
                "documentTitle",
                "content",
                "docContent",
                "folderId",
            ),
            "docs.append_doc": (
                "docId",
                "documentId",
                "fileId",
                "targetId",
                "docName",
                "fileName",
                "content",
            ),
            "docs.create_doc": ("title", "docTitle", "targetName", "fileName", "documentTitle", "content", "docContent", "folderId", "targetFolderId"),
            "docs.append_doc": ("docId", "documentId", "fileId", "targetId", "docName", "targetName", "fileName", "title", "content"),
            "docs.delete_doc": ("docId", "documentId", "fileId", "targetId", "docName", "targetName", "fileName"),
            "sheets.read_sheet": (
                "spreadsheetId",
                "sheetId",
                "fileId",
                "targetId",
                "sheetName",
                "targetName",
                "fileName",
                "title",
                "query",
                "range",
                "rangeName",
                "sheetTab",
            ),
            "sheets.search_sheet": ("query", "sheetName", "targetName", "folderId", "limit"),
            "sheets.create_sheet": ("title", "sheetTitle", "sheetName", "targetName", "fileName"),
            "sheets.append_row": (
                "spreadsheetId",
                "sheetId",
                "fileId",
                "targetId",
                "sheetName",
                "targetName",
                "fileName",
                "title",
                "query",
                "sheetTab",
                "rowData",
                "content",
                "values",
            ),
            "sheets.update_cell": (
                "spreadsheetId",
                "sheetId",
                "fileId",
                "targetId",
                "sheetName",
                "targetName",
                "fileName",
                "title",
                "query",
                "sheetTab",
                "cell",
                "range",
                "rangeName",
                "value",
            ),
            "sheets.delete_sheet": ("spreadsheetId", "sheetId", "fileId", "targetId", "sheetName", "targetName", "fileName"),
        }

        for tool_name, field_names in expected_fields.items():
            start = prepare_code.index(f"'{tool_name}':")
            end = prepare_code.find("\n  '", start + 1)
            block = prepare_code[start:] if end == -1 else prepare_code[start:end]
            for field_name in field_names:
                self.assertIn(field_name, block, f"{tool_name} should preserve {field_name}")

    def test_calendar_gateway_preserves_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        expected_fields = {
            "calendar.find_event": ("query", "calendarId", "dateFrom", "dateTo", "limit"),
            "calendar.create_event": (
                "summary",
                "title",
                "startAt",
                "start",
                "endAt",
                "end",
                "timezone",
                "description",
                "location",
                "calendarId",
            ),
            "calendar.delete_event": ("eventId", "query", "calendarId"),
            "calendar.check_availability": ("calendarId", "date", "startAt", "start", "endAt", "end"),
        }

        for tool_name, field_names in expected_fields.items():
            start = prepare_code.index(f"'{tool_name}':")
            end = prepare_code.find("\n  '", start + 1)
            block = prepare_code[start:] if end == -1 else prepare_code[start:end]
            for field_name in field_names:
                self.assertIn(field_name, block, f"{tool_name} should preserve {field_name}")

    def test_gmail_read_email_gateway_preserves_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        start = prepare_code.index("'gmail.read_email':")
        end = prepare_code.find("\n  '", start + 1)
        block = prepare_code[start:] if end == -1 else prepare_code[start:end]
        for field_name in ("messageId", "query", "sender", "subject"):
            self.assertIn(field_name, block, f"gmail.read_email should preserve {field_name}")

    def test_gmail_search_email_gateway_preserves_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        start = prepare_code.index("'gmail.search_email':")
        end = prepare_code.find("\n  '", start + 1)
        block = prepare_code[start:] if end == -1 else prepare_code[start:end]
        for field_name in ("query", "sender", "subject", "limit"):
            self.assertIn(field_name, block, f"gmail.search_email should preserve {field_name}")

    def test_gmail_reply_email_gateway_preserves_structured_fields(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])

        start = prepare_code.index("'gmail.reply_email':")
        end = prepare_code.find("\n  '", start + 1)
        block = prepare_code[start:] if end == -1 else prepare_code[start:end]
        for field_name in ("messageId", "searchQuery", "body"):
            self.assertIn(field_name, block, f"gmail.reply_email should preserve {field_name}")

    def test_phase5_gateway_supports_remaining_google_structured_actions(self) -> None:
        gateway_path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        gateway = json.loads(gateway_path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in gateway["nodes"] if node.get("name") == "Prepare Tool Request")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        route_node = next(node for node in gateway["nodes"] if node.get("name") == "Route Tool")
        route_code = str(route_node["parameters"]["jsCode"])

        expected_fields = {
            "calendar.find_free_slot": ("date", "startAt", "endAt", "durationMinutes", "calendarId"),
            "calendar.reschedule_event": ("eventId", "query", "startAt", "endAt", "timezone", "calendarId"),
            "gmail.search_email": ("query", "sender", "subject", "limit"),
            "gmail.search_by_sender": ("sender", "query", "subject", "limit"),
            "gmail.mark_read": ("messageId", "query", "sender", "subject"),
            "gmail.archive": ("messageId", "query", "sender", "subject"),
            "gmail.reply_email": ("messageId", "searchQuery", "body"),
            "docs.update_doc": (
                "docId",
                "documentId",
                "fileId",
                "targetId",
                "docName",
                "fileName",
                "title",
                "content",
            ),
            "sheets.update_range": (
                "spreadsheetId",
                "sheetId",
                "fileId",
                "targetId",
                "sheetName",
                "fileName",
                "title",
                "query",
                "sheetTab",
                "range",
                "rangeName",
                "cell",
                "content",
                "values",
            ),
        }

        for tool_name, field_names in expected_fields.items():
            start = prepare_code.index(f"'{tool_name}':")
            end = prepare_code.find("\n  '", start + 1)
            block = prepare_code[start:] if end == -1 else prepare_code[start:end]
            for field_name in field_names:
                self.assertIn(field_name, block, f"{tool_name} should preserve {field_name}")

        gmail_sender_start = prepare_code.index("'gmail.search_by_sender':")
        gmail_sender_end = prepare_code.find("\n  '", gmail_sender_start + 1)
        gmail_sender_block = (
            prepare_code[gmail_sender_start:]
            if gmail_sender_end == -1
            else prepare_code[gmail_sender_start:gmail_sender_end]
        )
        self.assertIn("workflowKey: 'gmail.search_email'", gmail_sender_block)

        for workflow_name in (
            "Sub-workflow: Google Calendar - Find Free Slot",
            "Sub-workflow: Google Calendar - Reschedule Event",
            "Sub-workflow: Google Gmail - Mark Read",
            "Sub-workflow: Google Gmail - Archive Email",
            "Sub-workflow: Google Docs - Update Doc",
            "Sub-workflow: Google Sheets - Update Range",
        ):
            self.assertIn(workflow_name, prepare_code)

        self.assertIn("source.workflowLookup && source.workflowName", route_code)

    def test_docs_update_doc_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_update_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("targetId: docId", prepare_code)
        self.assertIn("targetName: docName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_docs_create_doc_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_create_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)
        self.assertIn("args.targetFolderId", prepare_code)
        self.assertIn("ctx.payload.targetFolderId", prepare_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_docs_append_doc_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_append_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("ctx.payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("documentId", resolve_code)
        self.assertIn("fileId", resolve_code)
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        build_node = next(node for node in workflow["nodes"] if node.get("name") == "Build Append Request")
        build_code = str(build_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", build_code)
        self.assertIn("resolved.targetId", build_code)
        self.assertIn("targetName", build_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_docs_read_doc_leaf_consumes_structured_aliases_and_max_chars(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_read_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("source.maxChars", prepare_code)
        self.assertIn("args.maxChars", prepare_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)
        self.assertIn("source.maxChars", format_code)

    def test_docs_search_doc_leaf_consumes_structured_filters(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_search_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.args", prepare_code)
        self.assertIn("args.query", prepare_code)
        self.assertIn("args.docName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("args.folderId", prepare_code)
        self.assertIn("docName: query", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Search Docs")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("$json.folderId || 'root'", search_json)

    def test_sheets_search_sheet_leaf_consumes_structured_filters(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_search_sheet.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.args", prepare_code)
        self.assertIn("args.query", prepare_code)
        self.assertIn("args.sheetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("args.folderId", prepare_code)
        self.assertIn("targetName: cleanQuery", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Search Sheets")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("$json.folderId || 'root'", search_json)

    def test_docs_delete_doc_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "docs" / "workflow_sub_google_docs_delete_doc.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("ctx.payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("documentId", resolve_code)
        self.assertIn("fileId", resolve_code)
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_sheets_read_sheet_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_read_sheet.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("rangeName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)
        self.assertIn("rangeName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.sheetName", format_code)

    def test_sheets_create_sheet_leaf_consumes_target_name(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_create_sheet.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)

    def test_sheets_append_row_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_append_row.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("ctx.payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_sheets_update_cell_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_update_cell.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("ctx.payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)
        self.assertIn("source.rangeName", prepare_code)
        self.assertIn("args.rangeName", prepare_code)
        self.assertIn("ctx.payload.rangeName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)
        self.assertIn("rangeName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_sheets_delete_sheet_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_delete_sheet.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("ctx.payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("ctx.payload.targetName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_sheets_update_range_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "sheets" / "workflow_sub_google_sheets_update_range.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("targetId", prepare_code)
        self.assertIn("targetName", prepare_code)
        self.assertIn("rangeName", prepare_code)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

        build_node = next(node for node in workflow["nodes"] if node.get("name") == "Build Update Request")
        build_code = str(build_node["parameters"]["jsCode"])
        self.assertIn("targetId", build_code)
        self.assertIn("targetName", build_code)
        self.assertIn("rangeName", build_code)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Action")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", format_code)

    def test_gmail_read_email_leaf_prefers_message_id_when_available(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_read_email.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        node_names = {node.get("name") for node in workflow["nodes"]}
        self.assertIn("Co Message ID?", node_names)
        self.assertIn("Gmail Get Message By ID", node_names)

        get_by_id = next(node for node in workflow["nodes"] if node.get("name") == "Gmail Get Message By ID")
        get_by_id_json = json.dumps(get_by_id, ensure_ascii=False)
        self.assertIn("https://gmail.googleapis.com/gmail/v1/users/me/messages/", get_by_id_json)
        self.assertIn("format=full", get_by_id_json)

        format_node = next(node for node in workflow["nodes"] if node.get("name") == "Format Noi Dung Email")
        format_code = str(format_node["parameters"]["jsCode"])
        self.assertIn("collectPayloadText", format_code)
        self.assertIn("usedMessageId", format_code)

    def test_gmail_search_email_leaf_consumes_structured_filters(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_search_email.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Chuan Bi Tim Email")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.args", prepare_code)
        self.assertIn("args.query", prepare_code)
        self.assertIn("args.sender", prepare_code)
        self.assertIn("args.subject", prepare_code)
        self.assertIn("args.limit", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Gmail Search")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("from:' + $json.sender", search_json)
        self.assertIn("subject:' + $json.subject", search_json)

    def test_drive_search_file_leaf_consumes_structured_filters(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_search_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.args", prepare_code)
        self.assertIn("args.query", prepare_code)
        self.assertIn("args.fileName", prepare_code)
        self.assertIn("args.mimeType", prepare_code)
        self.assertIn("args.folderId", prepare_code)
        self.assertIn("args.limit", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Search File")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("$json.folderId || 'root'", search_json)
        self.assertIn("$json.mimeType", search_json)

    def test_gmail_reply_email_leaf_prefers_direct_message_id_and_body(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_reply_email.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Parse Tra Loi Email")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.messageId", prepare_code)
        self.assertIn("args.messageId", prepare_code)
        self.assertIn("source.body", prepare_code)
        self.assertIn("args.body", prepare_code)
        self.assertIn("source.searchQuery", prepare_code)
        self.assertIn("args.searchQuery", prepare_code)

        reply_node = next(node for node in workflow["nodes"] if node.get("name") == "Gmail Reply")
        reply_json = json.dumps(reply_node, ensure_ascii=False)
        self.assertIn('"messageId": "={{ $json.messageId }}"', reply_json)
        self.assertIn('"message": "={{ $json.replyBody }}"', reply_json)

    def test_drive_delete_file_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_delete_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("payload.targetId", prepare_code)
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("folderId", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim File Xoa")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("targetName", search_json)
        self.assertIn("folderId", search_json)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetId", resolve_code)
        self.assertIn("targetName", resolve_code)

    def test_drive_share_file_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_share_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("source.targetId", prepare_code)
        self.assertIn("args.targetId", prepare_code)
        self.assertIn("payload.targetId", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim File Share")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("targetName", search_json)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetName", resolve_code)
        self.assertIn("targetId", resolve_code)

    def test_drive_copy_file_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_copy_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("source.targetFolderName", prepare_code)
        self.assertIn("args.targetFolderName", prepare_code)
        self.assertIn("payload.targetFolderName", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim File Copy")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("targetName", search_json)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetName", resolve_code)
        self.assertIn("targetFolderName", resolve_code)

    def test_drive_move_file_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_move_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("source.targetFolderName", prepare_code)
        self.assertIn("args.targetFolderName", prepare_code)
        self.assertIn("payload.targetFolderName", prepare_code)

        file_search = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim File Move")
        file_search_json = json.dumps(file_search, ensure_ascii=False)
        self.assertIn("targetName", file_search_json)

        folder_search = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim Folder Move")
        folder_search_json = json.dumps(folder_search, ensure_ascii=False)
        self.assertIn("targetFolderName", folder_search_json)

        resolve_file = next(node for node in workflow["nodes"] if node.get("name") == "Resolve File Result")
        resolve_file_code = str(resolve_file["parameters"]["jsCode"])
        self.assertIn("targetName", resolve_file_code)
        self.assertIn("targetFolderName", resolve_file_code)

    def test_drive_rename_file_leaf_consumes_structured_aliases(self) -> None:
        path = ROOT / "execution" / "integrations" / "google" / "drive" / "workflow_sub_google_drive_rename_file.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        prepare_node = next(node for node in workflow["nodes"] if node.get("name") == "Prepare Action")
        prepare_code = str(prepare_node["parameters"]["jsCode"])
        self.assertIn("source.targetName", prepare_code)
        self.assertIn("args.targetName", prepare_code)
        self.assertIn("payload.targetName", prepare_code)
        self.assertIn("source.newName", prepare_code)
        self.assertIn("args.newName", prepare_code)
        self.assertIn("payload.newName", prepare_code)

        search_node = next(node for node in workflow["nodes"] if node.get("name") == "Drive Tim File Rename")
        search_json = json.dumps(search_node, ensure_ascii=False)
        self.assertIn("targetName", search_json)

        resolve_node = next(node for node in workflow["nodes"] if node.get("name") == "Resolve Search Result")
        resolve_code = str(resolve_node["parameters"]["jsCode"])
        self.assertIn("targetName", resolve_code)
        self.assertIn("newName", resolve_code)

    def test_error_monitor_has_chat_id_fallback(self) -> None:
        path = ROOT / "execution" / "monitors" / "workflow_error_monitor.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        if_node = next(node for node in workflow["nodes"] if node.get("name") == "Co Gui Bao Loi?")
        telegram_node = next(node for node in workflow["nodes"] if node.get("name") == "Gui Loi Telegram")
        classify_node = next(node for node in workflow["nodes"] if node.get("name") == "Classify Error")

        if_expr = str(if_node["parameters"]["conditions"]["boolean"][0]["value1"])
        chat_id_expr = str(telegram_node["parameters"]["bodyParameters"]["parameters"][0]["value"])
        classify_code = str(classify_node["parameters"]["jsCode"])

        self.assertIn("execution?.error?.context?.request?.body?.chat_id", if_expr)
        self.assertIn("TELEGRAM_ADMIN_CHAT_ID", if_expr)
        self.assertIn("execution?.error?.context?.request?.body?.chat_id", chat_id_expr)
        self.assertIn("TELEGRAM_ADMIN_CHAT_ID", chat_id_expr)
        self.assertIn("currentExecutionId", classify_code)
        self.assertIn("errorResponse?.executionId", classify_code)
        self.assertIn("skipNotify = isParentCascade", classify_code)
        self.assertIn("propagatedExecutionId !== currentExecutionId", classify_code)

    def test_workflow_validator_accepts_current_gateway_and_monitor(self) -> None:
        gateway = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        github_master = ROOT / "execution" / "integrations" / "github" / "workflow_sub_github_master.json"
        gmail_send = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_send_email.json"
        gmail_draft = ROOT / "execution" / "integrations" / "google" / "gmail" / "workflow_sub_google_gmail_draft_email.json"
        error_monitor = ROOT / "execution" / "monitors" / "workflow_error_monitor.json"

        self.assertEqual(validate_workflow_file(gateway), [])
        self.assertEqual(validate_workflow_file(github_master), [])
        self.assertEqual(validate_workflow_file(gmail_send), [])
        self.assertEqual(validate_workflow_file(gmail_draft), [])
        self.assertEqual(validate_workflow_file(error_monitor), [])

    def test_workflow_validator_rejects_human_readable_subworkflow_id(self) -> None:
        bad_workflow = {
            "name": "Mia: Tool Gateway",
            "nodes": [
                {
                    "name": "Route Tool",
                    "type": "n8n-nodes-base.code",
                    "parameters": {
                        "jsCode": "const workflowMap = { 'web.master': 'Sub-workflow: Web Master' };",
                    },
                }
            ],
            "connections": {},
        }

        issues = validate_workflow_data(bad_workflow, source="<memory>")
        self.assertTrue(any("web.master" in issue for issue in issues), issues)
        self.assertTrue(any("does not look like a workflow ID" in issue for issue in issues), issues)
