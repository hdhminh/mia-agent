from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from agent.i18n import t

from agent.skills.registry import DETERMINISTIC_DIRECT_TOOLS, DIRECT_TOOL_DEFAULT_ARGS

from agent.brain.parsers import (
    RequestProfile,
    normalize_query_text,
    keyword_matches,
    any_keyword_matches,
    looks_multi_step,
    is_soft_followup_only,
    strip_prefixes,
    strip_conversational_fillers,
    extract_sheet_range,
    _calendar_range_from_text,
    extract_github_repo_context,
    extract_news_topic,
    news_topic_to_feed_slug,
    looks_like_news_request,
    extract_shortlink_parts,
    extract_first_url,
)
from agent.brain.parsers.common import SOFT_FOLLOWUP_PATTERN, GENERAL_TOOL_OVERVIEW_CUES
from agent.brain.parsers.google import (
    _infer_google_service,
    _infer_calendar_hint,
    _infer_gmail_hint,
    _infer_workspace_hint,
    _infer_maps_hint,
)
from agent.brain.parsers.github import (
    _infer_github_hint,
    GITHUB_ACCOUNT_REPO_CUES,
    GITHUB_REPO_SEARCH_CUES,
)
from agent.brain.parsers.media import (
    _infer_media_hint,
)


def is_general_tool_overview_request(text: str) -> bool:
    normalized = normalize_query_text(text)
    if not normalized:
        return False
    if not any(cue in normalized for cue in GENERAL_TOOL_OVERVIEW_CUES):
        return False
    domain_cues = (
        "gmail",
        "mail",
        "email",
        "calendar",
        "lich",
        "lịch",
        "drive",
        "docs",
        "doc",
        "sheet",
        "sheets",
        "weather",
        "thoi tiet",
        "gia vang",
        "vang",
        "news",
        "tin tuc",
        "search",
        "shortlink",
        "memory",
    )
    return not any(keyword_matches(normalized, cue) for cue in domain_cues)

def is_current_time_request(normalized: str) -> bool:
    if not normalized:
        return False
    patterns = (
        r"\bhom nay la thu may\b",
        r"\bhom nay thu may\b",
        r"\bthu may hom nay\b",
        r"\bthu may\b",
        r"\bhom nay la ngay may\b",
        r"\bngay may hom nay\b",
        r"\bngay may\b",
        r"\bngay bao nhieu\b",
        r"\bmay gio\b",
        r"\bgio hien tai\b",
        r"\bgio bay gio\b",
        r"\bthoi gian hien tai\b",
        r"\bcurrent time\b",
        r"\bcurrent date\b",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def infer_request_profile(text: str, metadata: dict[str, Any] | None = None) -> RequestProfile:
    normalized = normalize_query_text(text)
    if not normalized:
        return RequestProfile(domain="general", hint_tool="", direct_confident=False, reason="empty request")

    if is_general_tool_overview_request(text):
        return RequestProfile(
            domain="general",
            hint_tool="__capabilities_overview__",
            direct_confident=False,
            reason="general capability overview",
        )

    if looks_like_news_request(text):
        news_topic = extract_news_topic(text)
        if news_topic and not news_topic_to_feed_slug(news_topic):
            return RequestProfile(domain="general", hint_tool="search_web", direct_confident=True, reason="news topic needs web search")
        return RequestProfile(domain="general", hint_tool="news_get", direct_confident=True, reason="explicit news request")

    if any_keyword_matches(normalized, ("thoi tiet", "weather", "nhiet do", "nhiệt độ", "du bao", "dự báo")):
        return RequestProfile(domain="general", hint_tool="weather_get", direct_confident=True, reason="weather request")

    if is_current_time_request(normalized):
        return RequestProfile(domain="general", hint_tool="time_now", direct_confident=True, reason="current date/time request")

    if any_keyword_matches(normalized, ("gia vang", "sjc", "gold")):
        return RequestProfile(domain="general", hint_tool="gold_get_price", direct_confident=True, reason="gold request")

    if any_keyword_matches(normalized, ("ban con nho gi", "ban còn nhớ gì", "nho gi gan day", "nhớ gì gần đây", "memory gan day", "da luu gi", "đã lưu gì")):
        return RequestProfile(domain="general", hint_tool="memory_recent", direct_confident=True, reason="memory recent request")

    if any_keyword_matches(normalized, ("shortlink", "short link", "rut gon link", "rút gọn link", "tao link ngan", "tạo link ngắn")):
        return RequestProfile(domain="general", hint_tool="shortlink_create", direct_confident=True, reason="shortlink request")

    if any_keyword_matches(normalized, ("task", "tasks", "việc cần làm", "viec can lam", "to-do", "todo", "nhiem vu", "nhiệm vụ", "nhac nho", "nhắc nhở", "cong viec", "công việc", "remind", "reminder")):
        if any_keyword_matches(normalized, ("quá hạn", "qua han", "overdue")):
            return RequestProfile(domain="workspace", hint_tool="tasks_list_overdue", direct_confident=True, reason="overdue tasks request")
        if any_keyword_matches(normalized, ("đến hạn", "den han", "due", "hôm nay", "hom nay")):
            return RequestProfile(domain="workspace", hint_tool="tasks_list_due", direct_confident=True, reason="due tasks request")
        if any_keyword_matches(normalized, ("tạo", "tao", "thêm", "them", "create", "add")):
            return RequestProfile(domain="workspace", hint_tool="tasks_create", direct_confident=False, reason="task create request")
        return RequestProfile(domain="workspace", hint_tool="tasks_list", direct_confident=True, reason="tasks request")

    if any_keyword_matches(normalized, ("contact", "contacts", "danh bạ", "danh ba", "người liên hệ", "nguoi lien he")):
        return RequestProfile(domain="workspace", hint_tool="contacts_search", direct_confident=True, reason="contacts request")

    if any_keyword_matches(normalized, ("automation", "tự động hóa", "tu dong hoa", "nhắc định kỳ", "nhac dinh ky")):
        if any_keyword_matches(normalized, ("danh sách", "danh sach", "list", "đang có", "dang co")):
            return RequestProfile(domain="general", hint_tool="automation_list", direct_confident=True, reason="automation list request")
        return RequestProfile(domain="general", hint_tool="automation_create", direct_confident=False, reason="automation request")

    smarthome_device_cues = (
        "smart home",
        "nha thong minh",
        "home assistant",
        "google home",
        "cast",
        "loa",
        "speaker",
        "den",
        "đèn",
        "quat",
        "quạt",
        "may lanh",
        "máy lạnh",
        "dieu hoa",
        "điều hòa",
        "air purifier",
        "may loc khong khi",
        "máy lọc không khí",
        "cong tac",
        "công tắc",
        "switch",
        "scene",
        "ngu phong",
        "phong ngu",
        "phòng ngủ",
        "phong tam",
        "phòng tắm",
        "tuya",
        "xiaomi",
    )
    if any_keyword_matches(normalized, smarthome_device_cues):
        if any_keyword_matches(normalized, ("help", "huong dan", "hướng dẫn", "lam duoc gi", "làm được gì")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_help", direct_confident=True, reason="smart home help request")
        if any_keyword_matches(normalized, ("khu vuc", "khu vực", "phong nao", "phòng nào", "areas", "rooms")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_list_areas", direct_confident=True, reason="smart home area list request")
        if any_keyword_matches(normalized, ("trang thai", "trạng thái", "status", "dang bat gi", "đang bật gì", "dang mo gi", "đang mở gì")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_room_status", direct_confident=False, reason="smart home status request")
        if any_keyword_matches(normalized, ("scene", "ngu canh", "ngữ cảnh")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_run_scene", direct_confident=True, reason="smart home scene request")
        if any_keyword_matches(normalized, ("tang toc quat", "tăng tốc quạt", "quat quay", "quạt quay", "bat quat quay", "bật quạt quay", "tat quat quay", "tắt quạt quay")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_run_scene", direct_confident=True, reason="smart home fan scene request")
        if any_keyword_matches(normalized, ("thong bao", "thông báo", "doc loa", "đọc loa", "noi loa", "nói loa", "tts")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_announce", direct_confident=False, reason="smart home announce request")
        if any_keyword_matches(normalized, ("am luong", "âm lượng", "volume", "play", "pause", "stop", "phat nhac", "phát nhạc")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_set_media", direct_confident=False, reason="smart home media request")
        if any_keyword_matches(normalized, ("do sang", "độ sáng", "brightness", "mau den", "màu đèn", "color temp", "nhiet mau", "nhiệt màu")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_set_light", direct_confident=False, reason="smart home light setting request")
        if any_keyword_matches(normalized, ("nhiet do", "nhiệt độ", "hvac", "cool", "heat", "dry", "fan mode", "swing")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_set_climate", direct_confident=False, reason="smart home climate request")
        if any_keyword_matches(normalized, ("toc do quat", "tốc độ quạt", "percentage", "preset mode", "speed")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_set_fan", direct_confident=False, reason="smart home fan request")
        if any_keyword_matches(normalized, ("bat", "bật", "mo", "mở", "turn on")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_turn_on", direct_confident=True, reason="smart home turn on request")
        if any_keyword_matches(normalized, ("tat", "tắt", "dong", "đóng", "turn off")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_turn_off", direct_confident=True, reason="smart home turn off request")
        if any_keyword_matches(normalized, ("dao", "đảo", "toggle")):
            return RequestProfile(domain="smarthome", hint_tool="smarthome_toggle", direct_confident=True, reason="smart home toggle request")
        return RequestProfile(domain="smarthome", hint_tool="smarthome_list_devices", direct_confident=False, reason="smart home request")

    from agent.brain.parsers.common import HELP_REQUEST_CUES
    help_request = any(keyword_matches(normalized, cue) for cue in HELP_REQUEST_CUES)

    if any_keyword_matches(normalized, ("github help", "help github", "github huong dan", "github hướng dẫn", "help repo github")):
        return RequestProfile(domain="github", hint_tool="github_help", direct_confident=True, reason="github help request")

    if any_keyword_matches(normalized, GITHUB_ACCOUNT_REPO_CUES):
        return RequestProfile(domain="github", hint_tool="github_list_user_repos", direct_confident=True, reason="github account repos request")

    if any_keyword_matches(normalized, GITHUB_REPO_SEARCH_CUES):
        return RequestProfile(domain="github", hint_tool="github_search_repos", direct_confident=True, reason="github repo search request")

    github_context = extract_github_repo_context(text, metadata)
    if github_context:
        hint_tool, direct_confident = _infer_github_hint(normalized, metadata, help_request)
        return RequestProfile(domain="github", hint_tool=hint_tool, direct_confident=direct_confident, reason="github repo request")

    explicit_url = ""
    if metadata:
        explicit_url = str(
            metadata.get("url")
            or metadata.get("link")
            or metadata.get("sourceUrl")
            or metadata.get("source_url")
            or ""
        ).strip()
    explicit_url = explicit_url or extract_first_url(text)
    if explicit_url:
        from agent.brain.parsers.web import URL_SUMMARY_CUES, URL_ASK_CUES, URL_READ_CUES
        if any_keyword_matches(normalized, URL_SUMMARY_CUES):
            return RequestProfile(domain="general", hint_tool="summarize_url", direct_confident=True, reason="specific url summary request")
        if any_keyword_matches(normalized, URL_ASK_CUES):
            return RequestProfile(domain="general", hint_tool="ask_url", direct_confident=False, reason="specific url question request")
        if any_keyword_matches(normalized, URL_READ_CUES) or normalize_query_text(text) == normalize_query_text(explicit_url):
            return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")
        return RequestProfile(domain="general", hint_tool="read_url", direct_confident=True, reason="specific url read request")

    from agent.brain.parsers.web import URL_ASK_CUES
    if any_keyword_matches(normalized, URL_ASK_CUES):
        return RequestProfile(domain="general", hint_tool="ask_url", direct_confident=False, reason="url follow-up request")

    media_hint, media_confident = _infer_media_hint(normalized, metadata, help_request)
    if media_hint:
        if media_hint == "drive_upload_file":
            return RequestProfile(
                domain="workspace",
                hint_tool=media_hint,
                direct_confident=True,
                reason="attachment save request",
            )
        if media_hint == "tts_speak":
            return RequestProfile(
                domain="media",
                hint_tool=media_hint,
                direct_confident=media_confident,
                reason="voice output request",
            )
        return RequestProfile(
            domain="media",
            hint_tool=media_hint,
            direct_confident=media_confident,
            reason="media attachment request",
        )

    domain = _infer_google_service(normalized)

    if domain == "calendar":
        hint_tool, direct_confident = _infer_calendar_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason="calendar domain")
    if domain == "gmail":
        hint_tool, direct_confident = _infer_gmail_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason="gmail domain")
    if domain == "maps":
        hint_tool, direct_confident = _infer_maps_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason="maps domain")
    if domain == "google_full":
        return RequestProfile(domain=domain, hint_tool="", direct_confident=False, reason="multi-google domain")
    if domain == "workspace":
        hint_tool, direct_confident = _infer_workspace_hint(normalized, help_request)
        return RequestProfile(domain=domain, hint_tool=hint_tool, direct_confident=direct_confident, reason=f"{domain} domain")

    if any_keyword_matches(normalized, ("tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet", "cho tôi biết", "thong tin ve", "thông tin về")):
        if not re.search(r"\b(tin tuc|tin tức|doc bao|đọc báo|bao hom nay|báo hôm nay|bao moi|báo mới|tin moi|tin mới|news)\b", normalized):
            return RequestProfile(domain="general", hint_tool="search_web", direct_confident=True, reason="web search request")

    return RequestProfile(domain="general", hint_tool="", direct_confident=False, reason="fallback general reasoning")


def tool_hint_for_request(text: str, metadata: dict[str, Any] | None = None) -> str:
    return infer_request_profile(text, metadata).hint_tool


def should_allow_direct_route(
    hint_tool: str,
    request_text: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    normalized = normalize_query_text(request_text)
    if hint_tool == "github_get_file" and any_keyword_matches(
        normalized,
        (
            "readme",
            "tóm tắt readme",
            "tom tat readme",
            "summary readme",
            "summarize readme",
            "overview readme",
        ),
    ):
        return False
    profile = infer_request_profile(request_text, metadata)
    return bool(hint_tool) and hint_tool in DETERMINISTIC_DIRECT_TOOLS and profile.direct_confident

from agent.brain.planning.direct_args import build_direct_tool_args
