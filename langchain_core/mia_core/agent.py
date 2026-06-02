from __future__ import annotations

import re
from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware, before_model
from langchain.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage, ToolMessage
from langchain_core.messages import trim_messages
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from mia_core import capabilities as caps
from mia_core.config import Settings
from mia_core.direct_executor import DirectExecutor, build_memory_recent_text
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
from mia_core.request_parser import looks_multi_step as parser_looks_multi_step
from mia_core.response_normalizer import (
    coerce_message_text as normalized_coerce_message_text,
    ensure_tool_links as normalized_ensure_tool_links,
    extract_tools_called as normalized_extract_tools_called,
    prefer_docs_search_output as normalized_prefer_docs_search_output,
    prefer_tool_truth as normalized_prefer_tool_truth,
    resolve_fallback_text as normalized_resolve_fallback_text,
    sanitize_final_text as normalized_sanitize_final_text,
)
from mia_core.router import route_request
from mia_core.tools import build_tools


SYSTEM_PROMPT = """Bạn là Mia, trợ lý AI chính của hệ thống.

Quy tắc:
- Trả lời bằng tiếng Việt tự nhiên, rõ ràng, vừa đủ ý.
- Xưng là "Mia", gọi người dùng là "anh Minh".
- Không lộ suy nghĩ nội bộ, không in <think>.
- Không dùng markdown đậm/nghiêng/code kiểu **text**, *text*, `code`. Hãy trả plain text phù hợp Telegram.
- Nếu không cần tool thì trả lời trực tiếp.
- Nếu cần dữ liệu hiện tại hoặc thao tác tích hợp thì gọi tool phù hợp.
- Nếu người dùng hỏi cách dùng, help, hướng dẫn, hoặc liệt kê khả năng của Gmail, Calendar, Drive, Docs, Sheets hay Shortlink, Mia phải gọi đúng tool liên quan thay vì tự mô tả chung chung.
- Nếu người dùng hỏi thời tiết, giá vàng, tin tức, tìm kiếm web, hoặc yêu cầu tích hợp Google/shortlink, ưu tiên dùng tool thật thay vì trả lời theo trí nhớ.
- Sau khi tool trả kết quả, Mia phải đọc kết quả đó và tự trả lời lại cho người dùng.
- Kết quả tool quan trọng hơn suy đoán.
- Với câu hỏi lặp lại về dữ liệu hiện tại như thời tiết, giá vàng, tin tức, hãy trả lời như một câu mới. Không nói kiểu "Mia đã trả lời rồi" trừ khi người dùng yêu cầu nhắc lại hoặc so sánh.
- Mặc định chỉ giải quyết yêu cầu mới nhất của người dùng trong lượt hiện tại.
- Không được tự mang kết quả hay chủ đề của lượt trước sang lượt này trừ khi người dùng nói rõ là muốn tiếp tục, so sánh, nhắc lại, hoặc dựa trên câu trước.
- Nếu tool lỗi, nói thật là tool lỗi và gợi ý bước tiếp theo nếu phù hợp.
- Dùng memory_search khi cần nhớ thông tin từ trước.
- Dùng memory_recent khi người dùng hỏi Mia còn nhớ gì, đã lưu gì gần đây, hoặc muốn xem nhanh memory gần đây.
- Dùng memory_write khi người dùng muốn Mia ghi nhớ điều bền vững.
"""

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
    "general": MEMORY_TOOL_NAMES + ["search_web"],
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


def _coerce_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item["text"]))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "")


def _sanitize_final_text(text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1: \2", cleaned)
    cleaned = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
    cleaned = re.sub(r"(?m)^\s*[-*]\s+", "- ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned
    return "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."


def _current_turn_messages(messages: list[Any]) -> list[Any]:
    last_human_index = -1
    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            last_human_index = index
    if last_human_index == -1:
        return messages
    return messages[last_human_index:]


def _normalize_query_text(text: str) -> str:
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


def _tool_hint_for_request(text: str) -> str:
    normalized = _normalize_query_text(text)
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


def _looks_multi_step(text: str) -> bool:
    normalized = _normalize_query_text(text)
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


def _strip_prefixes(text: str, prefixes: tuple[str, ...]) -> str:
    original = " ".join(str(text or "").strip().split())
    normalized = _normalize_query_text(original)
    for prefix in prefixes:
        normalized_prefix = _normalize_query_text(prefix)
        if normalized == normalized_prefix:
            return ""
        if normalized.startswith(normalized_prefix + " "):
            return original[len(prefix) :].strip()
    return original


def _extract_metric(text: str, label: str) -> str:
    pattern = rf"{re.escape(label)}\s*:\s*(.+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _split_nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _format_link_block(urls: list[str], label: str = "Link tham khảo") -> str:
    unique: list[str] = []
    for url in urls:
        clean = url.strip()
        if clean and clean not in unique:
            unique.append(clean)
    if not unique:
        return ""
    lines = ["", f"{label}:"]
    for index, url in enumerate(unique[:3], start=1):
        lines.append(f"{index}. {url}")
    return "\n".join(lines)


def _extract_list_items(raw_text: str) -> list[dict[str, str]]:
    lines = _split_nonempty_lines(raw_text)
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for line in lines:
        numbered = re.match(r"^(\d+)\.\s*(.+)$", line)
        if numbered:
            if current:
                items.append(current)
            current = {"title": numbered.group(2).strip()}
            continue

        if current is None:
            continue

        if line.lower().startswith("link:"):
            current.setdefault("links", [])
            current["links"] = [*current.get("links", []), line.split(":", 1)[1].strip()]
        elif line.startswith("http://") or line.startswith("https://"):
            current.setdefault("links", [])
            current["links"] = [*current.get("links", []), line.strip()]
        elif any(line.startswith(prefix) for prefix in ("👤", "🕒", "Loại:", "Sửa lúc:", "ID:", "Range:", "Mở ")):
            current.setdefault("details", [])
            current["details"] = [*current.get("details", []), line]
        else:
            current.setdefault("details", [])
            current["details"] = [*current.get("details", []), line]

    if current:
        items.append(current)
    return items


def _naturalize_direct_response(tool_name: str, raw_text: str, request_text: str) -> str:
    text = str(raw_text or "").strip()
    if not text:
        return text

    if tool_name == "weather_get":
        requested_location = _direct_tool_args("weather_get", request_text).get("location") or "đó"
        temp = _extract_metric(text, "Nhiệt độ")
        status = _extract_metric(text, "Tình trạng")
        humidity = _extract_metric(text, "Độ ẩm")
        wind = _extract_metric(text, "Gió")
        day_range = _extract_metric(text, "Nhiệt độ trong ngày")
        rain = _extract_metric(text, "Lượng mưa")
        parts = [f"Hiện tại ở {requested_location}, {('trời ' + status.lower()) if status else 'thời tiết khá ổn'}."]
        if temp:
            parts.append(f"Nhiệt độ khoảng {temp}.")
        details: list[str] = []
        if humidity:
            details.append(f"độ ẩm {humidity}")
        if wind:
            details.append(f"gió {wind}")
        if rain and rain != "0.0 mm":
            details.append(f"mưa {rain}")
        if day_range:
            details.append(f"nhiệt độ trong ngày {day_range}")
        if details:
            parts.append("Mia ghi nhận " + ", ".join(details) + ".")
        return " ".join(parts)

    if tool_name == "gold_get_price":
        updated = _extract_metric(text, "Cập nhật")
        buy = _extract_metric(text, "Mua vào")
        sell = _extract_metric(text, "Bán ra")
        parts = ["Giá vàng SJC 9999 hiện tại đã có rồi anh Minh."]
        if updated:
            parts.append(f"Dữ liệu cập nhật lúc {updated}.")
        if buy or sell:
            parts.append(f"Mua vào {buy or 'chưa rõ'}, bán ra {sell or 'chưa rõ'}.")
        return " ".join(parts)

    if tool_name == "shortlink_create":
        short_url = _extract_metric(text, "Short URL")
        expires = _extract_metric(text, "Hết hạn")
        original = _extract_metric(text, "Link gốc")
        parts = ["Mia đã rút gọn link xong rồi anh Minh."]
        if short_url:
            parts.append(f"Link ngắn là {short_url}.")
        if expires:
            parts.append(f"Nó sẽ hết hạn vào {expires}.")
        if original:
            parts.append(f"Link gốc vẫn là {original}.")
        return " ".join(parts)

    if tool_name == "memory_recent":
        lines = _split_nonempty_lines(text)
        if len(lines) <= 1:
            return text
        return "Mia đang nhớ mấy điều gần đây như sau:\n" + "\n".join(f"- {line}" for line in lines[1:4])

    if tool_name == "gmail_list_inbox":
        items = _extract_list_items(text)[:3]
        if not items:
            return "Hộp thư hiện chưa có email mới đáng chú ý."
        lines = [f"Hộp thư của anh Minh hiện có {len(items)} email nổi bật gần đây:"]
        links: list[str] = []
        for index, item in enumerate(items, start=1):
            sender = ""
            time_line = ""
            for detail in item.get("details", []):
                if detail.startswith("👤"):
                    sender = detail.replace("👤", "").strip().strip('"')
                elif detail.startswith("🕒"):
                    time_line = detail.replace("🕒", "").strip()
            sentence = f"{index}. {item.get('title', 'Không rõ tiêu đề')}"
            extra = []
            if sender:
                extra.append(f"từ {sender}")
            if time_line:
                extra.append(f"lúc {time_line}")
            if extra:
                sentence += " (" + ", ".join(extra) + ")"
            lines.append(sentence)
            links.extend(item.get("links", []))
        return "\n".join(lines) + _format_link_block(links, "Mở nhanh email")

    if tool_name in {"docs_search_doc", "drive_list_files", "drive_search_file", "sheets_search_sheet", "search_web", "news_get"}:
        items = _extract_list_items(text)[:3]
        if not items:
            return text
        intro_map = {
            "docs_search_doc": "Mia tìm thấy vài tài liệu khá khớp:",
            "drive_list_files": "Mia thấy vài file gần đây trong Drive:",
            "drive_search_file": "Mia tìm thấy vài file phù hợp trong Drive:",
            "sheets_search_sheet": "Mia thấy vài bảng tính phù hợp:",
            "search_web": "Mia tìm được vài kết quả web đáng tham khảo:",
            "news_get": "Mia gom nhanh vài tin nổi bật cho anh Minh:",
        }
        lines = [intro_map.get(tool_name, "Mia tìm thấy vài mục phù hợp:")]
        links: list[str] = []
        for index, item in enumerate(items, start=1):
            detail_text = ""
            for detail in item.get("details", []):
                normalized_detail = detail.lower()
                if normalized_detail.startswith("sua luc:") or normalized_detail.startswith("sửa lúc:") or normalized_detail.startswith("loại:"):
                    detail_text = detail
                    break
            line = f"{index}. {item.get('title', 'Không rõ tên')}"
            if detail_text:
                line += f" ({detail_text})"
            lines.append(line)
            links.extend(item.get("links", []))
        label_map = {
            "docs_search_doc": "Mở tài liệu",
            "drive_list_files": "Mở file",
            "drive_search_file": "Mở file",
            "sheets_search_sheet": "Mở bảng tính",
            "search_web": "Link tham khảo",
            "news_get": "Đọc thêm",
        }
        return "\n".join(lines) + _format_link_block(links, label_map.get(tool_name, "Link tham khảo"))

    if tool_name in {"calendar_list_today", "calendar_list_tomorrow"}:
        items = _extract_list_items(text)[:3]
        if not items:
            return "Hôm nay anh Minh chưa có lịch nào." if tool_name == "calendar_list_today" else "Ngày mai anh Minh chưa có lịch nào."
        heading = "Hôm nay anh Minh có mấy lịch sau:" if tool_name == "calendar_list_today" else "Ngày mai anh Minh có mấy lịch sau:"
        lines = [heading]
        links: list[str] = []
        for index, item in enumerate(items, start=1):
            time_line = ""
            for detail in item.get("details", []):
                if "🕒" in detail:
                    time_line = detail.replace("🕒", "").strip()
                    break
            line = f"{index}. {item.get('title', 'Không rõ tiêu đề')}"
            if time_line:
                line += f" ({time_line})"
            lines.append(line)
            links.extend(item.get("links", []))
        return "\n".join(lines) + _format_link_block(links, "Mở lịch")

    if tool_name in {"calendar_help", "gmail_help", "drive_help", "docs_help", "sheets_help"}:
        lines = _split_nonempty_lines(text)
        if len(lines) <= 2:
            return text
        intro = lines[0]
        body = [line for line in lines[1:] if not line.lower().startswith("ví dụ")]
        body = body[:5]
        return f"{intro}\n" + "\n".join(f"- {line}" for line in body if line)

    return text


def _extract_shortlink_parts(text: str) -> tuple[str, str]:
    match = re.search(r"https?://[^\s<>\"']+", text or "", flags=re.IGNORECASE)
    if not match:
        return "", ""
    url = match.group(0).rstrip("),.;!?")
    ttl = " ".join((text or "").replace(url, " ").split()).strip()
    ttl = _strip_prefixes(ttl, ("rut gon link", "tao link ngan", "shortlink", "short link"))
    return url, ttl


def _direct_tool_args(tool_name: str, request_text: str) -> dict[str, Any]:
    text = " ".join(str(request_text or "").strip().split())

    if tool_name == "weather_get":
        location = _strip_prefixes(
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
        topic = _strip_prefixes(text, ("tin tuc", "tin tức", "news", "doc bao", "đọc báo", "bao hom nay", "báo hôm nay"))
        return {"topic": topic.strip()}

    if tool_name == "search_web":
        query = _strip_prefixes(
            text,
            ("tim", "tìm", "tim kiem", "tìm kiếm", "search", "tra cuu", "tra cứu", "cho toi biet ve", "cho tôi biết về", "thong tin ve", "thông tin về"),
        )
        return {"query": query.strip()}

    if tool_name == "shortlink_create":
        url, ttl = _extract_shortlink_parts(text)
        return {"url": url, "ttl": ttl}

    if tool_name == "docs_search_doc":
        query = _strip_prefixes(text, ("tim doc", "tìm doc", "search doc", "tim tai lieu", "tìm tài liệu"))
        return {"query": query.strip(), "docName": query.strip(), "limit": 3}

    if tool_name == "drive_search_file":
        query = _strip_prefixes(text, ("tim file", "tìm file", "search file", "tim trong drive", "tìm trong drive", "tim tep", "tìm tệp"))
        return {"query": query.strip(), "fileName": query.strip(), "limit": 3}

    if tool_name == "sheets_search_sheet":
        query = _strip_prefixes(text, ("tim sheet", "tìm sheet", "search sheet", "tim bang tinh", "tìm bảng tính"))
        return {"query": query.strip(), "sheetName": query.strip(), "limit": 3}

    if tool_name == "gmail_search_email":
        query = _strip_prefixes(text, ("tim mail", "tìm mail", "tim email", "tìm email", "search mail", "search email"))
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


def _fallback_memory_recent_text(memory_repo: MemoryRepository, chat_id: str, limit: int = 5) -> str:
    rows = memory_repo.recent(chat_id=chat_id, limit=max(1, min(limit, 10)))
    if not rows:
        return "Mia chưa có memory nào đáng chú ý gần đây."

    lines = ["Memory gần đây:"]
    for index, row in enumerate(rows, start=1):
        memory_type = str(row.get("memory_type") or "general").strip()
        title = str(row.get("title") or "").strip()
        content = str(row.get("content") or row.get("chunk_text") or "").strip()
        snippet = content[:220].rstrip()
        if len(content) > 220:
            snippet += "..."
        prefix = f"{index}. [{memory_type}]"
        if title:
            prefix += f" {title}:"
        lines.append(f"{prefix} {snippet}".strip())
    return "\n".join(lines)


def _resolve_fallback_text(messages: list[Any]) -> str:
    for message in reversed(_current_turn_messages(messages)):
        if isinstance(message, AIMessage):
            text = _sanitize_final_text(_coerce_message_text(message.content))
            if text and "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng" not in text:
                return text
        if isinstance(message, ToolMessage):
            text = _coerce_message_text(message.content).strip()
            if text:
                return text
    return "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."


def _extract_tools_called(messages: list[Any]) -> list[str]:
    calls: list[str] = []
    for message in _current_turn_messages(messages):
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for item in tool_calls:
            name = str(item.get("name") or "").strip()
            if name and name not in calls:
                calls.append(name)
    return calls


def _extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for url in re.findall(r"https?://[^\s)>\]]+", text or ""):
        cleaned = url.rstrip(".,;")
        if cleaned not in seen:
            seen.append(cleaned)
    return seen


def _looks_like_not_found(text: str) -> bool:
    normalized = _normalize_query_text(text)
    cues = (
        "khong tim thay",
        "khong thay",
        "chua tim thay",
        "khong co ket qua",
        "khong co thong tin",
    )
    return any(cue in normalized for cue in cues)


def _tool_messages_by_name(messages: list[Any], tool_name: str) -> list[str]:
    texts: list[str] = []
    current_tool_name = ""
    for message in _current_turn_messages(messages):
        if isinstance(message, AIMessage):
            tool_calls = getattr(message, "tool_calls", None) or []
            if tool_calls:
                current_tool_name = str(tool_calls[-1].get("name") or "").strip()
        elif isinstance(message, ToolMessage):
            if current_tool_name == tool_name:
                text = _coerce_message_text(message.content).strip()
                if text:
                    texts.append(text)
    return texts


def _all_tool_messages(messages: list[Any]) -> list[str]:
    texts: list[str] = []
    for message in _current_turn_messages(messages):
        if isinstance(message, ToolMessage):
            text = _coerce_message_text(message.content).strip()
            if text:
                texts.append(text)
    return texts


def _prefer_tool_truth(final_text: str, messages: list[Any], tools_called: list[str]) -> str:
    if not _looks_like_not_found(final_text):
        return final_text

    url_tools = {
        "docs_search_doc",
        "drive_search_file",
        "drive_list_files",
        "search_web",
        "news_get",
        "gmail_list_inbox",
    }
    if not any(tool in url_tools for tool in tools_called):
        return final_text

    for tool_text in _all_tool_messages(messages):
        if _extract_urls(tool_text):
            return _sanitize_final_text(tool_text)
    return final_text


def _prefer_docs_search_output(request_text: str, final_text: str, messages: list[Any], tools_called: list[str]) -> str:
    if "docs_search_doc" not in tools_called:
        return final_text

    normalized = _normalize_query_text(request_text)
    search_cues = ("tim doc", "search doc", "tim tai lieu", "doc project", "tai lieu")
    if not any(cue in normalized for cue in search_cues):
        return final_text

    for tool_text in _tool_messages_by_name(messages, "docs_search_doc"):
        if _extract_urls(tool_text):
            return _sanitize_final_text(tool_text)
    return final_text


def _ensure_tool_links(
    final_text: str,
    messages: list[Any],
    tools_called: list[str],
    *,
    tool_name: str,
    label: str,
    limit: int,
) -> str:
    if tool_name not in tools_called:
        return final_text
    if _extract_urls(final_text):
        return final_text

    urls: list[str] = []
    for tool_text in _tool_messages_by_name(messages, tool_name):
        for url in _extract_urls(tool_text):
            if url not in urls:
                urls.append(url)

    if not urls:
        return final_text

    lines = [final_text.rstrip(), "", label]
    for index, url in enumerate(urls[:limit], start=1):
        lines.append(f"{index}. {url}")
    return "\n".join(lines).strip()


def _build_trim_history_middleware(max_tokens: int):
    @before_model
    def trim_history(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if len(messages) <= 6:
            return None

        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            token_counter="approximate",
            strategy="last",
            start_on="human",
            allow_partial=False,
        )
        if len(trimmed) >= len(messages):
            return None
        return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), *trimmed]}

    return trim_history


class MiaAgentService:
    def __init__(
        self,
        *,
        settings: Settings,
        memory_repo: MemoryRepository,
        tool_gateway: N8nToolGatewayClient,
        checkpointer: PostgresSaver,
    ) -> None:
        self.settings = settings
        self.memory_repo = memory_repo
        self.tool_gateway = tool_gateway
        self.checkpointer = checkpointer
        self.model = self._build_model()
        self.tool_registry = self._build_tool_registry()
        self.direct_executor = DirectExecutor(
            memory_repo=self.memory_repo,
            tool_gateway=self.tool_gateway,
        )
        self.agents = self._build_agents()

    def _build_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            model=self.settings.model,
            api_key=self.settings.openrouter_api_key,
            base_url=self.settings.openrouter_base_url,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
            default_headers={
                "HTTP-Referer": self.settings.openrouter_referer,
                "X-Title": self.settings.openrouter_title,
            },
        )

    def _build_tool_registry(self) -> dict[str, Any]:
        tools = build_tools(
            memory_repo=self.memory_repo,
            tool_gateway=self.tool_gateway,
        )
        return {tool.name: tool for tool in tools}

    def _build_agent(self, tool_names: list[str]):
        tools = [self.tool_registry[name] for name in tool_names]
        return create_agent(
            model=self.model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            context_schema=MiaContext,
            checkpointer=self.checkpointer,
            middleware=[
                _build_trim_history_middleware(self.settings.history_max_tokens),
                ModelRetryMiddleware(max_retries=1),
                ToolRetryMiddleware(max_retries=1),
            ],
        )

    def _build_agents(self) -> dict[str, Any]:
        return {name: self._build_agent(tool_names) for name, tool_names in caps.AGENT_TOOLSETS.items()}

    def _choose_agent_key(self, hint_tool: str, request_text: str) -> str:
        if parser_looks_multi_step(request_text):
            if hint_tool.startswith(("calendar_", "gmail_", "drive_", "docs_", "sheets_")):
                return "google_full"
            return "general"

        if hint_tool.startswith("calendar_"):
            return "calendar"
        if hint_tool.startswith("gmail_"):
            return "gmail"
        if hint_tool.startswith(("drive_", "docs_", "sheets_")):
            return "workspace"
        return "general"

    def _try_direct_route(
        self,
        request: MiaChatRequest,
        context: MiaContext,
        hint_tool: str,
        *,
        allow_multistep: bool = False,
    ) -> MiaChatResponse | None:
        return self.direct_executor.execute(
            request,
            context,
            hint_tool,
            allow_multistep=allow_multistep,
        )

    def _summarize_tool_result(self, user_text: str, tool_text: str) -> str:
        result = self.model.invoke(
            [
                SystemMessage(
                    content=(
                        "Bạn là Mia. Hãy đọc kết quả tool rồi trả lời lại cho người dùng "
                        "bằng tiếng Việt tự nhiên, ngắn gọn, dễ hiểu. "
                        "Ưu tiên nội dung chính, không lặp máy móc, không để trống, không dùng markdown."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Yêu cầu gốc của người dùng:\n{user_text}\n\n"
                        f"Kết quả tool:\n{tool_text}\n\n"
                        "Hãy viết câu trả lời cuối cùng cho người dùng trong 1 đến 4 câu."
                    )
                ),
            ]
        )
        return normalized_sanitize_final_text(normalized_coerce_message_text(result.content))

    def chat(self, request: MiaChatRequest) -> MiaChatResponse:
        thread_id = request.resolved_thread_id()
        request_id = request.resolved_request_id()
        context = MiaContext(
            chat_id=request.chat_id,
            user_id=request.resolved_user_id(),
            timezone=self.settings.timezone,
            request_id=request_id,
        )
        route = route_request(request.text)
        hint_tool = route.hint_tool

        direct_response = self._try_direct_route(request, context, hint_tool)
        if direct_response is not None:
            return direct_response

        agent_key = route.agent_key or self._choose_agent_key(hint_tool, request.text)
        agent = self.agents[agent_key]

        messages_payload: list[dict[str, str]] = []
        if hint_tool:
            messages_payload.append(
                {
                    "role": "system",
                    "content": f"Với yêu cầu này, ưu tiên dùng tool {hint_tool} trước nếu phù hợp.",
                }
            )
        messages_payload.append(
            {
                "role": "system",
                "content": (
                    "Chỉ xử lý yêu cầu mới nhất trong lượt này. "
                    "Nếu không có chỉ dẫn tiếp tục rõ ràng, bỏ qua chủ đề và kết quả của lượt trước."
                ),
            }
        )
        messages_payload.append({"role": "user", "content": request.text})

        try:
            result = agent.invoke(
                {"messages": messages_payload},
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": self.settings.recursion_limit,
                },
                context=context,
            )
        except GraphRecursionError:
            fallback_response = self._try_direct_route(
                request,
                context,
                hint_tool,
                allow_multistep=True,
            )
            if fallback_response is not None:
                return fallback_response
            raise

        messages = list(result.get("messages", []))
        final_message = messages[-1] if messages else AIMessage(content="")
        final_text = normalized_sanitize_final_text(normalized_coerce_message_text(final_message.content))
        tools_called = normalized_extract_tools_called(messages)
        if not tools_called and hint_tool == "memory_recent":
            final_text = build_memory_recent_text(self.memory_repo, request.chat_id)
            tools_called = ["memory_recent"]
        if (
            tools_called
            and final_text == "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."
        ):
            tool_text = normalized_resolve_fallback_text(messages)
            summarized = self._summarize_tool_result(request.text, tool_text)
            final_text = summarized or tool_text
        final_text = normalized_prefer_docs_search_output(request.text, final_text, messages, tools_called)
        final_text = normalized_prefer_tool_truth(final_text, messages, tools_called)
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="search_web",
            label="Link tham khảo:",
            limit=3,
        )
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="news_get",
            label="Link tham khảo:",
            limit=3,
        )
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="docs_search_doc",
            label="Link tài liệu:",
            limit=3,
        )
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="drive_search_file",
            label="Link file tham khảo:",
            limit=3,
        )
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="drive_list_files",
            label="Link file gần đây:",
            limit=3,
        )
        final_text = normalized_ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="gmail_list_inbox",
            label="Link email:",
            limit=3,
        )
        return MiaChatResponse(
            final_text=final_text,
            tools_called=tools_called,
            thread_id=thread_id,
            request_id=request_id,
        )
