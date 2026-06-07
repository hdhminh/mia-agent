from __future__ import annotations

from dataclasses import dataclass
import re

SOFT_FOLLOWUP_PATTERN = re.compile(
    r"\b(roi|rồi|tom tat|tóm tắt|noi ngan|nói ngắn|ngan gon|ngắn gọn|ngan|ngắn|gon|gọn|giup minh|giúp mình|giup toi|giúp tôi|cho minh|cho tôi)\b",
    flags=re.IGNORECASE,
)

HELP_REQUEST_CUES = (
    "tool",
    "tools",
    "tich hop",
    "tích hợp",
    "ho tro",
    "hỗ trợ",
    "huong dan",
    "hướng dẫn",
    "cach dung",
    "cách dùng",
    "lam duoc gi",
    "làm được gì",
    "co gi",
    "có gì",
    "dung the nao",
    "dùng thế nào",
)

GENERAL_TOOL_OVERVIEW_CUES = (
    "tool gi",
    "tool gì",
    "tool nao",
    "tool nào",
    "co nhung tool gi",
    "có những tool gì",
    "dang co nhung tool gi",
    "đang có những tool gì",
    "mia co cac tool gi",
    "mia có các tool gì",
    "mia co nhung gi",
    "mia có những gì",
    "mia lam duoc gi",
    "mia làm được gì",
    "danh sach tool",
    "liệt kê tool",
    "liet ke tool",
    "cac tool",
    "các tool",
)

GOOGLE_SERVICE_CUES: dict[str, tuple[str, ...]] = {
    "calendar": ("calendar", "lich", "lịch", "su kien", "sự kiện", "meeting", "cuoc hop", "cuộc họp", "phong van"),
    "gmail": ("gmail", "mail", "email", "inbox", "hop thu", "hộp thư", "thu den", "thư đến"),
    "drive": ("drive", "google drive", "folder", "thu muc", "thư mục", "tep", "tệp", "file", "file drive"),
    "docs": ("docs", "google docs", "google doc", "doc", "tai lieu", "tài liệu", "van ban", "văn bản", "document"),
    "sheets": ("sheets", "sheet", "bang tinh", "bảng tính", "spreadsheet"),
}

VIEW_ACTION_CUES = ("xem", "mo", "mở", "liet ke", "liệt kê", "check", "co gi", "có gì", "danh sach", "danh sách")
SEARCH_ACTION_CUES = ("tim", "tìm", "tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "loc", "lọc")
READ_ACTION_CUES = ("doc", "đọc", "chi tiet", "chi tiết", "noi dung", "nội dung", "thong tin", "thông tin")
CREATE_ACTION_CUES = ("tao", "tạo", "them", "thêm", "dat", "đặt", "lap", "lập", "book", "create")
DELETE_ACTION_CUES = ("xoa", "xóa", "huy", "hủy", "delete", "cancel", "bo", "bỏ")
SEND_ACTION_CUES = ("gui", "gửi", "send")
REPLY_ACTION_CUES = ("tra loi", "trả lời", "reply", "phan hoi", "phản hồi")
DRAFT_ACTION_CUES = ("soan", "soạn", "nhap", "nháp", "draft")
AVAILABILITY_ACTION_CUES = ("ranh", "freebusy", "availability", "trong lich", "trống lịch")
FREE_SLOT_ACTION_CUES = ("khoang trong", "khoảng trống", "free slot", "free time", "gio trong", "giờ trống", "ranh luc nao", "rảnh lúc nào")
RESCHEDULE_ACTION_CUES = ("doi lich", "đổi lịch", "doi gio", "đổi giờ", "reschedule", "move meeting", "postpone", "delay")
GMAIL_SENDER_CUES = ("nguoi gui", "người gửi", "from", "sender", "tu ", "từ ")
GMAIL_MARK_READ_CUES = ("danh dau da doc", "đánh dấu đã đọc", "mark as read", "mark read", "da doc", "đã đọc", "da xem", "đã xem")
GMAIL_ARCHIVE_CUES = ("archive", "luu tru", "lưu trữ", "don inbox", "dọn inbox", "remove from inbox")
UPLOAD_ACTION_CUES = ("upload", "tai len", "tải lên")
DOWNLOAD_ACTION_CUES = ("download", "tai xuong", "tải xuống", "tai file", "tải file")
SHARE_ACTION_CUES = ("share", "chia se", "chia sẻ")
MOVE_ACTION_CUES = ("move", "di chuyen", "di chuyển")
RENAME_ACTION_CUES = ("doi sen", "đổi tên", "rename")  # Keep original rename cue if there was any, wait: let's verify if rename cue was "doi sen" or "doi ten"
# Ah, line 203 of original was: RENAME_ACTION_CUES = ("doi ten", "đổi tên", "rename")
# Let's write "doi ten"
RENAME_ACTION_CUES = ("doi ten", "đổi tên", "rename")
COPY_ACTION_CUES = ("copy", "nhan ban", "nhân bản", "sao chep", "sao chép")
EXPORT_ACTION_CUES = ("export", "xuat", "xuất")
APPEND_ACTION_CUES = ("them vao", "thêm vào", "append", "ghi them", "ghi thêm", "them dong", "thêm dòng")
UPDATE_ACTION_CUES = ("cap nhat", "cập nhật", "update", "sua o", "sửa ô")
DOC_UPDATE_ACTION_CUES = ("cap nhat doc", "cập nhật doc", "cap nhat tai lieu", "cập nhật tài liệu", "sua doc", "sửa doc", "sua noi dung", "sửa nội dung", "replace doc", "overwrite doc")
SHEETS_RANGE_ACTION_CUES = ("range", "vung", "vùng", "khoang", "khoảng", "nhieu o", "nhiều ô", "update range", "cap nhat vung", "cập nhật vùng")


@dataclass(frozen=True)
class RequestProfile:
    domain: str
    hint_tool: str
    direct_confident: bool
    reason: str


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


def keyword_matches(normalized: str, keyword: str) -> bool:
    needle = normalize_query_text(keyword)
    if not needle:
        return False
    if " " in needle:
        return needle in normalized
    return re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", normalized) is not None


def any_keyword_matches(normalized: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword_matches(normalized, keyword) for keyword in keywords)


def _keyword_score(normalized: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if keyword_matches(normalized, keyword))


def _matches_action(normalized: str, action_cues: tuple[str, ...]) -> bool:
    return any_keyword_matches(normalized, action_cues)


def _looks_like_sheet_cell_reference(text: str) -> bool:
    return bool(re.search(r"\b[A-Z]{1,3}\d+\b", text or "", flags=re.IGNORECASE))


def _has_multi_service_connector(normalized: str) -> bool:
    return any(
        token in normalized
        for token in (
            " và ",
            " va ",
            " hoặc ",
            " hoac ",
            " cùng ",
            " cung ",
            " với ",
            " voi ",
            ",",
            ";",
            " / ",
        )
    )


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


def strip_conversational_fillers(text: str) -> str:
    text = " ".join(str(text or "").strip().split())
    if not text:
        return ""

    prefix_patterns = [
        r"^(sai\s+roi|sai\s+rồi|khong|không|nho|nhớ|quay\s+lai|quay\s+lại)[,\s]+",
        r"^(giup\s+minh|giup\s+toi|giúp\s+mình|giúp\s+tôi|giup|giúp|hay|hãy)\s+",
        r"^(cho\s+toi|cho\s+tôi|cho\s+minh|cho\s+mình)\s+",
    ]

    current = text
    changed = True
    while changed:
        changed = False
        for pattern in prefix_patterns:
            new_text = re.sub(pattern, "", current, flags=re.IGNORECASE).strip()
            if new_text != current:
                current = new_text
                changed = True
                break

    suffix_patterns = [
        r"[,\s]+(nhe|nhé|nha|nha,|nhe,|nhé,|nha\s+nhe|nha\s+nhé|nhe\s+nha|nhé\s+nha)$",
        r"\s+(voi|với|gium|giùm|giup|giúp)$",
        r"\s+(di|đi|nhi|nhỉ)$",
        r"\s+(duoc\s+khong|được\s+không|duoc\s+ko|được\s+ko)$",
    ]

    changed = True
    while changed:
        changed = False
        for pattern in suffix_patterns:
            new_text = re.sub(pattern, "", current, flags=re.IGNORECASE).strip()
            if new_text != current:
                current = new_text
                changed = True
                break

    return current
