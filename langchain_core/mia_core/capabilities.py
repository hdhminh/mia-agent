from __future__ import annotations

from typing import Any


MEMORY_TOOL_NAMES = ["memory_search", "memory_recent", "memory_write"]
SIMPLE_TOOL_NAMES = ["weather_get", "gold_get_price", "news_get", "search_web", "shortlink_create"]
CALENDAR_TOOL_NAMES = [
    "calendar_help",
    "calendar_list_today",
    "calendar_list_tomorrow",
    "calendar_find_event",
    "calendar_create_event",
    "calendar_delete_event",
    "calendar_check_availability",
]
GMAIL_TOOL_NAMES = [
    "gmail_help",
    "gmail_list_inbox",
    "gmail_read_email",
    "gmail_search_email",
    "gmail_send_email",
    "gmail_draft_email",
    "gmail_reply_email",
]
WORKSPACE_TOOL_NAMES = [
    "drive_help",
    "drive_list_files",
    "drive_search_file",
    "drive_get_file_info",
    "drive_create_folder",
    "drive_create_file",
    "drive_upload_file",
    "drive_download_file",
    "drive_share_file",
    "drive_move_file",
    "drive_rename_file",
    "drive_copy_file",
    "drive_delete_file",
    "drive_delete_folder",
    "drive_export_file",
    "docs_help",
    "docs_search_doc",
    "docs_read_doc",
    "docs_create_doc",
    "docs_append_doc",
    "docs_delete_doc",
    "sheets_help",
    "sheets_search_sheet",
    "sheets_read_sheet",
    "sheets_create_sheet",
    "sheets_append_row",
    "sheets_update_cell",
    "sheets_delete_sheet",
]
GOOGLE_FULL_TOOL_NAMES = CALENDAR_TOOL_NAMES + GMAIL_TOOL_NAMES + WORKSPACE_TOOL_NAMES

AGENT_TOOLSETS: dict[str, list[str]] = {
    "general": MEMORY_TOOL_NAMES + SIMPLE_TOOL_NAMES,
    "calendar": MEMORY_TOOL_NAMES + CALENDAR_TOOL_NAMES,
    "gmail": MEMORY_TOOL_NAMES + GMAIL_TOOL_NAMES,
    "workspace": MEMORY_TOOL_NAMES + WORKSPACE_TOOL_NAMES,
    "google_full": MEMORY_TOOL_NAMES + GOOGLE_FULL_TOOL_NAMES,
}

DIRECT_GATEWAY_TOOLS: dict[str, str] = {
    "weather_get": "weather.get",
    "gold_get_price": "gold.get_price",
    "news_get": "news.get",
    "search_web": "search.web",
    "shortlink_create": "shortlink.create",
    "calendar_help": "calendar.help",
    "calendar_list_today": "calendar.list_today",
    "calendar_list_tomorrow": "calendar.list_tomorrow",
    "calendar_find_event": "calendar.find_event",
    "calendar_create_event": "calendar.create_event",
    "calendar_delete_event": "calendar.delete_event",
    "calendar_check_availability": "calendar.check_availability",
    "gmail_help": "gmail.help",
    "gmail_list_inbox": "gmail.list_inbox",
    "gmail_read_email": "gmail.read_email",
    "gmail_search_email": "gmail.search_email",
    "gmail_send_email": "gmail.send_email",
    "gmail_draft_email": "gmail.draft_email",
    "gmail_reply_email": "gmail.reply_email",
    "drive_help": "drive.help",
    "drive_list_files": "drive.list_files",
    "drive_search_file": "drive.search_file",
    "drive_get_file_info": "drive.get_file_info",
    "drive_create_folder": "drive.create_folder",
    "drive_create_file": "drive.create_file",
    "drive_upload_file": "drive.upload_file",
    "drive_download_file": "drive.download_file",
    "drive_share_file": "drive.share_file",
    "drive_move_file": "drive.move_file",
    "drive_rename_file": "drive.rename_file",
    "drive_copy_file": "drive.copy_file",
    "drive_delete_file": "drive.delete_file",
    "drive_delete_folder": "drive.delete_folder",
    "drive_export_file": "drive.export_file",
    "docs_help": "docs.help",
    "docs_search_doc": "docs.search_doc",
    "docs_read_doc": "docs.read_doc",
    "docs_create_doc": "docs.create_doc",
    "docs_append_doc": "docs.append_doc",
    "docs_delete_doc": "docs.delete_doc",
    "sheets_help": "sheets.help",
    "sheets_search_sheet": "sheets.search_sheet",
    "sheets_read_sheet": "sheets.read_sheet",
    "sheets_create_sheet": "sheets.create_sheet",
    "sheets_append_row": "sheets.append_row",
    "sheets_update_cell": "sheets.update_cell",
    "sheets_delete_sheet": "sheets.delete_sheet",
}

DIRECT_TOOL_DEFAULT_ARGS: dict[str, dict[str, Any]] = {
    "drive_list_files": {"limit": 3},
    "drive_search_file": {"limit": 3},
    "docs_search_doc": {"limit": 3},
    "sheets_search_sheet": {"limit": 3},
}

DIRECT_ROUTE_TOOLS = set(DIRECT_GATEWAY_TOOLS) | {"memory_recent"}

# Read-only / low-side-effect capabilities that should stay on the cheap path
# even when users append style instructions like "rồi tóm tắt ngắn".
DETERMINISTIC_DIRECT_TOOLS = {
    "memory_recent",
    "weather_get",
    "gold_get_price",
    "news_get",
    "search_web",
    "shortlink_create",
    "calendar_help",
    "calendar_list_today",
    "calendar_list_tomorrow",
    "gmail_help",
    "gmail_list_inbox",
    "drive_help",
    "drive_list_files",
    "drive_search_file",
    "docs_help",
    "docs_search_doc",
    "sheets_help",
    "sheets_search_sheet",
}

DIRECT_FRIENDLY_MULTISTEP_TOOLS = set(DETERMINISTIC_DIRECT_TOOLS)
