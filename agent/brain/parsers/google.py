from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from agent.brain.parsers.common import (
    GOOGLE_SERVICE_CUES,
    SEND_ACTION_CUES,
    REPLY_ACTION_CUES,
    DRAFT_ACTION_CUES,
    READ_ACTION_CUES,
    SEARCH_ACTION_CUES,
    VIEW_ACTION_CUES,
    CREATE_ACTION_CUES,
    DELETE_ACTION_CUES,
    AVAILABILITY_ACTION_CUES,
    APPEND_ACTION_CUES,
    UPDATE_ACTION_CUES,
    UPLOAD_ACTION_CUES,
    DOWNLOAD_ACTION_CUES,
    SHARE_ACTION_CUES,
    MOVE_ACTION_CUES,
    RENAME_ACTION_CUES,
    COPY_ACTION_CUES,
    EXPORT_ACTION_CUES,
    RESCHEDULE_ACTION_CUES,
    FREE_SLOT_ACTION_CUES,
    GMAIL_MARK_READ_CUES,
    GMAIL_ARCHIVE_CUES,
    GMAIL_SENDER_CUES,
    DOC_UPDATE_ACTION_CUES,
    SHEETS_RANGE_ACTION_CUES,
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    _keyword_score,
    _matches_action,
    _looks_like_sheet_cell_reference,
    _has_multi_service_connector,
    strip_prefixes,
)


def _infer_google_service(normalized: str) -> str:
    service_scores = {
        service: _keyword_score(normalized, keywords)
        for service, keywords in GOOGLE_SERVICE_CUES.items()
    }
    if _looks_like_sheet_cell_reference(normalized):
        service_scores["sheets"] = max(service_scores["sheets"], 1)

    positive_services = [service for service, score in service_scores.items() if score > 0]
    if not positive_services:
        return ""
    if len(positive_services) > 1:
        if service_scores["maps"] > 0 and len(positive_services) == 1:
            return "maps"
        if _has_multi_service_connector(normalized):
            return "google_full"
        gmail_actions = (
            _matches_action(normalized, SEND_ACTION_CUES)
            or _matches_action(normalized, REPLY_ACTION_CUES)
            or _matches_action(normalized, DRAFT_ACTION_CUES)
            or _matches_action(normalized, READ_ACTION_CUES)
            or _matches_action(normalized, SEARCH_ACTION_CUES)
            or _matches_action(normalized, VIEW_ACTION_CUES)
        )
        calendar_actions = (
            _matches_action(normalized, CREATE_ACTION_CUES)
            or _matches_action(normalized, DELETE_ACTION_CUES)
            or _matches_action(normalized, AVAILABILITY_ACTION_CUES)
        )
        workspace_actions = (
            _matches_action(normalized, SEARCH_ACTION_CUES)
            or _matches_action(normalized, READ_ACTION_CUES)
            or _matches_action(normalized, VIEW_ACTION_CUES)
            or _matches_action(normalized, CREATE_ACTION_CUES)
            or _matches_action(normalized, DELETE_ACTION_CUES)
            or _matches_action(normalized, APPEND_ACTION_CUES)
            or _matches_action(normalized, UPDATE_ACTION_CUES)
            or _matches_action(normalized, UPLOAD_ACTION_CUES)
            or _matches_action(normalized, DOWNLOAD_ACTION_CUES)
            or _matches_action(normalized, SHARE_ACTION_CUES)
            or _matches_action(normalized, MOVE_ACTION_CUES)
            or _matches_action(normalized, RENAME_ACTION_CUES)
            or _matches_action(normalized, COPY_ACTION_CUES)
            or _matches_action(normalized, EXPORT_ACTION_CUES)
        )
        if service_scores["gmail"] > 0 and gmail_actions and not calendar_actions:
            return "gmail"
        if service_scores["sheets"] > 0 and (_looks_like_sheet_cell_reference(normalized) or _matches_action(normalized, UPDATE_ACTION_CUES) or _matches_action(normalized, APPEND_ACTION_CUES) or _matches_action(normalized, READ_ACTION_CUES) or _matches_action(normalized, SEARCH_ACTION_CUES) or _matches_action(normalized, VIEW_ACTION_CUES)):
            return "workspace"
        if service_scores["docs"] > 0 and workspace_actions:
            return "workspace"
        if service_scores["drive"] > 0 and workspace_actions:
            return "workspace"
        return "google_full"
    service = positive_services[0]
    if service == "maps":
        return "maps"
    if service in {"drive", "docs", "sheets"}:
        return "workspace"
    return service


def _infer_maps_hint(normalized: str, help_request: bool) -> tuple[str, bool]:
    if help_request:
        return "maps_help", True
    if any_keyword_matches(normalized, ("toa do", "tọa độ", "lat", "lng", "kinh do", "kinh độ", "vi do", "vĩ độ")) and (
        any_keyword_matches(normalized, ("dia chi", "địa chỉ", "o dau", "ở đâu", "gan dau", "gần đâu"))
        or _matches_action(normalized, READ_ACTION_CUES)
        or _matches_action(normalized, SEARCH_ACTION_CUES)
    ):
        return "maps_reverse_geocode", True
    if any_keyword_matches(normalized, ("chi duong", "chỉ đường", "duong di", "đường đi", "route", "bao xa", "mất bao lâu", "mat bao lau")):
        return "maps_compute_route", True
    if any_keyword_matches(normalized, ("place id", "ma dia diem", "mã địa điểm", "chi tiet dia diem", "chi tiết địa điểm")):
        return "maps_place_details", True
    if any_keyword_matches(normalized, ("gan day", "gần đây", "nearby", "quan an", "cafe", "nha hang", "nhà hàng", "khach san", "khách sạn", "atm", "dia diem", "địa điểm")):
        return "maps_search_place", True
    if any_keyword_matches(normalized, ("dia chi", "địa chỉ", "toa do", "tọa độ", "geocode")):
        return "maps_geocode", True
    return "maps_search_place", False


def _infer_calendar_hint(normalized: str, help_request: bool) -> tuple[str, bool]:
    if help_request:
        return "calendar_help", True
    if any_keyword_matches(normalized, RESCHEDULE_ACTION_CUES):
        return "calendar_reschedule_event", False
    if any_keyword_matches(normalized, FREE_SLOT_ACTION_CUES):
        return "calendar_find_free_slot", True
    if _matches_action(normalized, DELETE_ACTION_CUES):
        return "calendar_delete_event", False
    if _matches_action(normalized, CREATE_ACTION_CUES):
        return "calendar_create_event", False
    if _matches_action(normalized, AVAILABILITY_ACTION_CUES):
        return "calendar_check_availability", False
    if keyword_matches(normalized, "ngay mai") or keyword_matches(normalized, "mai"):
        if _matches_action(normalized, VIEW_ACTION_CUES) or keyword_matches(normalized, "lich"):
            return "calendar_list_tomorrow", True
    if keyword_matches(normalized, "hom nay"):
        if _matches_action(normalized, VIEW_ACTION_CUES) or keyword_matches(normalized, "lich"):
            return "calendar_list_today", True
    return "calendar_find_event", False


def _infer_gmail_hint(normalized: str, help_request: bool) -> tuple[str, bool]:
    if help_request:
        return "gmail_help", True
    if any_keyword_matches(normalized, GMAIL_MARK_READ_CUES):
        return "gmail_mark_read", False
    if any_keyword_matches(normalized, GMAIL_ARCHIVE_CUES):
        return "gmail_archive", False
    sender_cue = any_keyword_matches(normalized, GMAIL_SENDER_CUES)
    if sender_cue and (
        _matches_action(normalized, SEARCH_ACTION_CUES)
        or _matches_action(normalized, READ_ACTION_CUES)
        or _matches_action(normalized, VIEW_ACTION_CUES)
    ):
        return "gmail_search_by_sender", False
    if _matches_action(normalized, REPLY_ACTION_CUES):
        return "gmail_reply_email", False
    if _matches_action(normalized, DRAFT_ACTION_CUES):
        return "gmail_draft_email", False
    if _matches_action(normalized, SEND_ACTION_CUES):
        return "gmail_send_email", False
    if _matches_action(normalized, SEARCH_ACTION_CUES):
        if sender_cue:
            return "gmail_search_by_sender", False
        return "gmail_search_email", False
    if _matches_action(normalized, READ_ACTION_CUES):
        return "gmail_read_email", False
    if _matches_action(normalized, VIEW_ACTION_CUES) or keyword_matches(normalized, "inbox"):
        return "gmail_list_inbox", True
    return "gmail_list_inbox", False


def _infer_workspace_hint(normalized: str, help_request: bool) -> tuple[str, bool]:
    docs_score = _keyword_score(normalized, GOOGLE_SERVICE_CUES["docs"])
    sheets_score = _keyword_score(normalized, GOOGLE_SERVICE_CUES["sheets"])
    drive_score = _keyword_score(normalized, GOOGLE_SERVICE_CUES["drive"])
    if _looks_like_sheet_cell_reference(normalized):
        sheets_score = max(sheets_score, 1)

    if docs_score >= max(sheets_score, drive_score) and docs_score > 0:
        if help_request:
            return "docs_help", True
        if _matches_action(normalized, DELETE_ACTION_CUES):
            return "docs_delete_doc", False
        if _matches_action(normalized, APPEND_ACTION_CUES):
            return "docs_append_doc", False
        if _matches_action(normalized, UPDATE_ACTION_CUES) or any_keyword_matches(normalized, DOC_UPDATE_ACTION_CUES):
            return "docs_update_doc", False
        if _matches_action(normalized, CREATE_ACTION_CUES):
            return "docs_create_doc", False
        if _matches_action(normalized, SEARCH_ACTION_CUES):
            return "docs_search_doc", False
        if _matches_action(normalized, READ_ACTION_CUES) or _matches_action(normalized, VIEW_ACTION_CUES):
            return "docs_read_doc", False
        return "docs_search_doc", False

    if sheets_score >= max(docs_score, drive_score) and sheets_score > 0:
        if help_request:
            return "sheets_help", True
        if _matches_action(normalized, DELETE_ACTION_CUES):
            return "sheets_delete_sheet", False
        if _matches_action(normalized, UPDATE_ACTION_CUES):
            sheet_range = extract_sheet_range(normalized)
            if (":" in sheet_range) or any_keyword_matches(normalized, SHEETS_RANGE_ACTION_CUES):
                return "sheets_update_range", False
            return "sheets_update_cell", False
        if _matches_action(normalized, APPEND_ACTION_CUES):
            return "sheets_append_row", False
        if _matches_action(normalized, CREATE_ACTION_CUES):
            return "sheets_create_sheet", False
        if extract_sheet_range(normalized) and (_matches_action(normalized, READ_ACTION_CUES) or _matches_action(normalized, VIEW_ACTION_CUES) or _matches_action(normalized, SEARCH_ACTION_CUES)):
            return "sheets_read_range", True
        if _matches_action(normalized, READ_ACTION_CUES) or _matches_action(normalized, VIEW_ACTION_CUES):
            return "sheets_read_sheet", False
        return "sheets_search_sheet", False

    if help_request:
        return "drive_help", True
    if _matches_action(normalized, EXPORT_ACTION_CUES):
        return "drive_export_file", False
    if _matches_action(normalized, DELETE_ACTION_CUES):
        if keyword_matches(normalized, "folder") or keyword_matches(normalized, "thu muc"):
            return "drive_delete_folder", False
        return "drive_delete_file", False
    if _matches_action(normalized, COPY_ACTION_CUES):
        return "drive_copy_file", False
    if _matches_action(normalized, RENAME_ACTION_CUES):
        return "drive_rename_file", False
    if _matches_action(normalized, MOVE_ACTION_CUES):
        return "drive_move_file", False
    if _matches_action(normalized, SHARE_ACTION_CUES):
        return "drive_share_file", False
    if _matches_action(normalized, DOWNLOAD_ACTION_CUES):
        return "drive_download_file", False
    if _matches_action(normalized, UPLOAD_ACTION_CUES):
        return "drive_upload_file", False
    if _matches_action(normalized, CREATE_ACTION_CUES):
        if keyword_matches(normalized, "folder") or keyword_matches(normalized, "thu muc"):
            return "drive_create_folder", False
        return "drive_create_file", False
    if _matches_action(normalized, READ_ACTION_CUES):
        return "drive_get_file_info", False
    if _matches_action(normalized, SEARCH_ACTION_CUES):
        return "drive_search_file", False
    if _matches_action(normalized, VIEW_ACTION_CUES):
        return "drive_list_files", False
    return "drive_search_file", False


def extract_sheet_range(text: str) -> str:
    match = re.search(r"\b([A-Z]{1,3}\d+:[A-Z]{1,3}\d+|[A-Z]{1,3}\d+)\b", text or "", flags=re.IGNORECASE)
    return match.group(1).upper() if match else ""


def _calendar_range_from_text(text: str) -> tuple[str, str]:
    normalized = normalize_query_text(text)
    now = datetime.now()

    def start_of_day(dt: datetime) -> datetime:
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def end_of_day(dt: datetime) -> datetime:
        return dt.replace(hour=23, minute=59, second=59, microsecond=0)

    def next_weekday(base: datetime, target_py_weekday: int, next_week: bool = False) -> datetime:
        days_ahead = (target_py_weekday - base.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        if next_week:
            days_ahead += 7
        return start_of_day(base + timedelta(days=days_ahead))

    if "cuoi tuan nay" in normalized:
        saturday = next_weekday(now, 5, False)
        sunday = saturday + timedelta(days=1)
        return saturday.isoformat(timespec="seconds"), end_of_day(sunday).isoformat(timespec="seconds")
    if "cuoi tuan sau" in normalized:
        saturday = next_weekday(now, 5, True)
        sunday = saturday + timedelta(days=1)
        return saturday.isoformat(timespec="seconds"), end_of_day(sunday).isoformat(timespec="seconds")
    if "tuan sau" in normalized:
        monday = next_weekday(now, 0, True)
        sunday = monday + timedelta(days=6)
        return monday.isoformat(timespec="seconds"), end_of_day(sunday).isoformat(timespec="seconds")
    if "hom nay" in normalized:
        start = start_of_day(now)
        return start.isoformat(timespec="seconds"), end_of_day(start).isoformat(timespec="seconds")
    if "ngay mai" in normalized or re.search(r"\bmai\b", normalized):
        start = start_of_day(now + timedelta(days=1))
        return start.isoformat(timespec="seconds"), end_of_day(start).isoformat(timespec="seconds")

    weekday_map = {
        "thu 2": 0,
        "thu 3": 1,
        "thu 4": 2,
        "thu 5": 3,
        "thu 6": 4,
        "thu 7": 5,
        "chu nhat": 6,
    }
    for token, weekday in weekday_map.items():
        if token in normalized:
            target = next_weekday(now, weekday, "tuan sau" in normalized)
            return target.isoformat(timespec="seconds"), end_of_day(target).isoformat(timespec="seconds")

    return start_of_day(now).isoformat(timespec="seconds"), end_of_day(now).isoformat(timespec="seconds")
