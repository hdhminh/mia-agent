from __future__ import annotations

import re
from typing import Any

from mia_core.capabilities import DIRECT_FRIENDLY_MULTISTEP_TOOLS, DIRECT_TOOL_DEFAULT_ARGS


def normalize_query_text(text: str) -> str:
    normalized = " ".join(str(text or "").strip().lower().split())
    normalized = (
        normalized.replace("đ", "d")
        .replace("á", "a").replace("à", "a").replace("ả", "a").replace("ã", "a").replace("ạ", "a")
        .replace("ă", "a").replace("ắ", "a").replace("ằ", "a").replace("ẳ", "a").replace("ẵ", "a").replace("ặ", "a")
        .replace("â", "a").replace("ấ", "a").replace("ầ", "a").replace("ẩ", "a").replace("ẫ", "a").replace("ậ", "a")
        .replace("é", "e").replace("è", "e").replace("ẻ", "e").replace("ẽ", "e").replace("ẹ", "e")
        .replace("ê", "e").replace("ế", "e").replace("ề", "e").replace("ể", "e").replace("ễ", "e").replace("ệ", "e")
        .replace("í", "i").replace("ì", "i").replace("ỉ", "i").replace("ĩ", "i").replace("ị", "i")
        .replace("ó", "o").replace("ò", "o").replace("ỏ", "o").replace("õ", "o").replace("ọ", "o")
        .replace("ô", "o").replace("ố", "o").replace("ồ", "o").replace("ổ", "o").replace("ỗ", "o").replace("ộ", "o")
        .replace("ơ", "o").replace("ớ", "o").replace("ờ", "o").replace("ở", "o").replace("ỡ", "o").replace("ợ", "o")
        .replace("ú", "u").replace("ù", "u").replace("ủ", "u").replace("ũ", "u").replace("ụ", "u")
        .replace("ư", "u").replace("ứ", "u").replace("ừ", "u").replace("ử", "u").replace("ữ", "u").replace("ự", "u")
        .replace("ý", "y").replace("ỳ", "y").replace("ỷ", "y").replace("ỹ", "y").replace("ỵ", "y")
    )
    return normalized


def tool_hint_for_request(text: str) -> str:
    normalized = normalize_query_text(text)
    hint_map = [
        ("weather_get", ("thoi tiet", "weather", "nhiet do", "du bao")),
        ("gold_get_price", ("gia vang", "sjc", "gold")),
        ("news_get", ("tin tuc", "doc bao", "bao hom nay", "news")),
        ("memory_recent", ("ban con nho gi", "nho gi gan day", "memory gan day", "da luu gi")),
        ("calendar_help", ("calendar help", "lich help", "huong dan calendar", "huong dan lich")),
        ("calendar_list_tomorrow", ("lich ngay mai", "mai toi co gi", "ngay mai toi co gi")),
        ("calendar_list_today", ("lich hom nay", "hom nay toi co gi", "xem lich hom nay")),
        ("calendar_check_availability", ("lich ranh", "co ranh", "freebusy", "availability")),
        ("calendar_create_event", ("tao lich", "dat lich", "tao su kien", "book lich")),
        ("calendar_delete_event", ("xoa lich", "huy lich", "delete event", "cancel event")),
        ("calendar_find_event", ("calendar", "lich", "su kien", "hop")),
        ("gmail_help", ("gmail help", "mail help", "email help", "huong dan gmail", "huong dan mail")),
        ("gmail_search_email", ("tim mail", "tim email", "search mail", "search email")),
        ("gmail_read_email", ("doc mail", "doc email", "read mail", "read email", "chi tiet mail", "chi tiet email")),
        ("gmail_send_email", ("gui mail", "gui email", "send mail", "send email")),
        ("gmail_draft_email", ("soan mail", "soan email", "draft email", "draft mail")),
        ("gmail_reply_email", ("tra loi mail", "tra loi email", "reply mail", "reply email")),
        ("gmail_list_inbox", ("xem mail", "xem email", "inbox", "hop thu", "mail moi", "email moi")),
        ("drive_help", ("drive help", "huong dan drive", "google drive help")),
        ("drive_search_file", ("tim file", "search file", "tim trong drive", "tim tep", "search drive")),
        ("drive_get_file_info", ("chi tiet file", "thong tin file")),
        ("drive_create_folder", ("tao folder", "tao thu muc")),
        ("drive_create_file", ("tao file drive", "create file drive")),
        ("drive_upload_file", ("upload file", "tai len drive")),
        ("drive_download_file", ("tai file", "download file")),
        ("drive_share_file", ("share file", "chia se file")),
        ("drive_move_file", ("move file", "di chuyen file")),
        ("drive_rename_file", ("doi ten file", "rename file")),
        ("drive_copy_file", ("copy file", "nhan ban file")),
        ("drive_delete_folder", ("xoa folder", "xoa thu muc")),
        ("drive_delete_file", ("xoa file drive", "delete file")),
        ("drive_export_file", ("export file", "xuat file")),
        ("drive_list_files", ("xem file drive", "liet ke file drive", "file drive gan day", "drive")),
        ("docs_help", ("docs help", "doc help", "huong dan docs", "huong dan google docs")),
        ("docs_search_doc", ("tim doc", "search doc", "tim tai lieu", "google doc")),
        ("docs_read_doc", ("xem doc", "doc doc", "read doc", "noi dung doc")),
        ("docs_create_doc", ("tao doc", "tao tai lieu", "create doc")),
        ("docs_append_doc", ("them vao doc", "append doc", "ghi them vao tai lieu")),
        ("docs_delete_doc", ("xoa doc", "delete doc", "xoa tai lieu")),
        ("sheets_help", ("sheets help", "sheet help", "huong dan sheets")),
        ("sheets_search_sheet", ("tim sheet", "search sheet", "tim bang tinh")),
        ("sheets_read_sheet", ("xem sheet", "doc sheet", "read sheet")),
        ("sheets_create_sheet", ("tao sheet", "tao bang tinh", "create sheet")),
        ("sheets_append_row", ("them dong vao sheet", "append row")),
        ("sheets_update_cell", ("cap nhat sheet", "cap nhat o", "update cell")),
        ("sheets_delete_sheet", ("xoa sheet", "delete sheet", "xoa bang tinh")),
        ("shortlink_create", ("shortlink", "short link", "rut gon link", "tao link ngan")),
        ("search_web", ("tim ", "tim kiem", "search", "tra cuu", "cho toi biet", "thong tin ve")),
    ]
    for tool_name, keywords in hint_map:
        if any(keyword in normalized for keyword in keywords):
            return tool_name
    return ""


def looks_multi_step(text: str) -> bool:
    normalized = normalize_query_text(text)
    cues = (
        " roi ",
        " sau do ",
        " tiep theo ",
        " dong thoi ",
        " cung luc ",
        " va gui ",
        " va tao ",
        " va cap nhat ",
        " xong thi ",
    )
    padded = f" {normalized} "
    return any(cue in padded for cue in cues)


def is_soft_followup_only(text: str) -> bool:
    normalized = normalize_query_text(text)
    padded = f" {normalized} "
    if " roi " not in padded:
        return False

    hard_cues = (
        " sau do ",
        " tiep theo ",
        " dong thoi ",
        " cung luc ",
        " va gui ",
        " va tao ",
        " va cap nhat ",
        " xong thi ",
    )
    if any(cue in padded for cue in hard_cues):
        return False

    soft_cues = (
        " tom tat ",
        " noi ngan ",
        " ngan gon ",
        " gon gang ",
        " giup minh ",
        " giup toi ",
        " cho minh ",
        " cho toi ",
    )
    return any(cue in padded for cue in soft_cues)


def should_allow_direct_route(hint_tool: str, request_text: str) -> bool:
    if not hint_tool:
        return False
    if not looks_multi_step(request_text):
        return True
    if hint_tool not in DIRECT_FRIENDLY_MULTISTEP_TOOLS:
        return False
    return is_soft_followup_only(request_text)


def strip_prefixes(text: str, prefixes: tuple[str, ...]) -> str:
    original = " ".join(str(text or "").strip().split())
    normalized = normalize_query_text(original)
    for prefix in prefixes:
        normalized_prefix = normalize_query_text(prefix)
        if normalized == normalized_prefix:
            return ""
        if normalized.startswith(normalized_prefix + " "):
            return original[len(prefix) :].strip()
    return original


def extract_shortlink_parts(text: str) -> tuple[str, str]:
    match = re.search(r"https?://[^\s<>\"']+", text or "", flags=re.IGNORECASE)
    if not match:
        return "", ""
    url = match.group(0).rstrip("),.;!?")
    ttl = " ".join((text or "").replace(url, " ").split()).strip()
    ttl = strip_prefixes(ttl, ("rut gon link", "tao link ngan", "shortlink", "short link"))
    return url, ttl


def build_direct_tool_args(tool_name: str, request_text: str) -> dict[str, Any]:
    text = " ".join(str(request_text or "").strip().split())

    if tool_name == "weather_get":
        location = strip_prefixes(
            text,
            ("thoi tiet", "thời tiết", "weather", "nhiet do", "nhiệt độ", "du bao thoi tiet", "dự báo thời tiết"),
        )
        location = re.sub(r"^(tai|tại|o|ở|cho toi|cho tôi|hom nay|hôm nay)\s+", "", location, flags=re.IGNORECASE)
        location = re.sub(
            r"\b(hom nay|hôm nay|bay gio|bây giờ|the nao|thế nào|ra sao|nhu the nao|như thế nào)\b",
            "",
            location,
            flags=re.IGNORECASE,
        )
        return {"location": location.strip()}

    if tool_name == "news_get":
        topic = strip_prefixes(text, ("tin tuc", "tin tức", "news", "doc bao", "đọc báo", "bao hom nay", "báo hôm nay"))
        topic = re.sub(r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|giup minh|giúp mình)\b", "", topic, flags=re.IGNORECASE)
        return {"topic": topic.strip()}

    if tool_name == "search_web":
        query = strip_prefixes(
            text,
            ("tim", "tìm", "tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet ve", "cho tôi biết về", "thong tin ve", "thông tin về"),
        )
        query = re.sub(r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|giup minh|giúp mình)\b", "", query, flags=re.IGNORECASE)
        return {"query": query.strip()}

    if tool_name == "shortlink_create":
        url, ttl = extract_shortlink_parts(text)
        return {"url": url, "ttl": ttl}

    if tool_name == "docs_search_doc":
        query = strip_prefixes(text, ("tim doc", "tìm doc", "search doc", "tim tai lieu", "tìm tài liệu"))
        query = re.sub(r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|giup minh|giúp mình)\b", "", query, flags=re.IGNORECASE)
        return {"query": query.strip(), "docName": query.strip(), "limit": 3}

    if tool_name == "drive_search_file":
        query = strip_prefixes(text, ("tim file", "tìm file", "search file", "tim trong drive", "tìm trong drive", "tim tep", "tìm tệp"))
        query = re.sub(r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|giup minh|giúp mình)\b", "", query, flags=re.IGNORECASE)
        return {"query": query.strip(), "fileName": query.strip(), "limit": 3}

    if tool_name == "sheets_search_sheet":
        query = strip_prefixes(text, ("tim sheet", "tìm sheet", "search sheet", "tim bang tinh", "tìm bảng tính"))
        query = re.sub(r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|giup minh|giúp mình)\b", "", query, flags=re.IGNORECASE)
        return {"query": query.strip(), "sheetName": query.strip(), "limit": 3}

    if tool_name == "gmail_search_email":
        query = strip_prefixes(text, ("tim mail", "tìm mail", "tim email", "tìm email", "search mail", "search email"))
        return {"query": query.strip(), "instruction": text}

    if tool_name in {
        "calendar_find_event",
        "calendar_create_event",
        "calendar_delete_event",
        "calendar_check_availability",
        "gmail_read_email",
        "gmail_send_email",
        "gmail_draft_email",
        "gmail_reply_email",
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
        "docs_read_doc",
        "docs_create_doc",
        "docs_append_doc",
        "docs_delete_doc",
        "sheets_read_sheet",
        "sheets_create_sheet",
        "sheets_append_row",
        "sheets_update_cell",
        "sheets_delete_sheet",
    }:
        return {"instruction": text}

    return dict(DIRECT_TOOL_DEFAULT_ARGS.get(tool_name, {}))

