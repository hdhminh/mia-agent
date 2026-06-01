from __future__ import annotations

import re
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver

from mia_core.config import Settings
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
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
        self.agent = self._build_agent()

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

    def _build_agent(self):
        tools = build_tools(
            memory_repo=self.memory_repo,
            tool_gateway=self.tool_gateway,
        )
        return create_agent(
            model=self.model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            context_schema=MiaContext,
            checkpointer=self.checkpointer,
            middleware=[
                ModelRetryMiddleware(max_retries=2),
                ToolRetryMiddleware(max_retries=2),
            ],
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
        return _sanitize_final_text(_coerce_message_text(result.content))

    def chat(self, request: MiaChatRequest) -> MiaChatResponse:
        thread_id = request.resolved_thread_id()
        request_id = request.resolved_request_id()
        context = MiaContext(
            chat_id=request.chat_id,
            user_id=request.resolved_user_id(),
            timezone=self.settings.timezone,
            request_id=request_id,
        )
        hint_tool = _tool_hint_for_request(request.text)
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

        result = self.agent.invoke(
            {"messages": messages_payload},
            config={
                "configurable": {"thread_id": thread_id},
                "recursion_limit": self.settings.recursion_limit,
            },
            context=context,
        )

        messages = list(result.get("messages", []))
        final_message = messages[-1] if messages else AIMessage(content="")
        final_text = _sanitize_final_text(_coerce_message_text(final_message.content))
        tools_called = _extract_tools_called(messages)
        if not tools_called and hint_tool == "memory_recent":
            final_text = _fallback_memory_recent_text(self.memory_repo, request.chat_id)
            tools_called = ["memory_recent"]
        if (
            tools_called
            and final_text == "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."
        ):
            tool_text = _resolve_fallback_text(messages)
            summarized = self._summarize_tool_result(request.text, tool_text)
            final_text = summarized or tool_text
        final_text = _prefer_docs_search_output(request.text, final_text, messages, tools_called)
        final_text = _prefer_tool_truth(final_text, messages, tools_called)
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="search_web",
            label="Link tham khảo:",
            limit=3,
        )
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="news_get",
            label="5 link tham khảo:",
            limit=5,
        )
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="docs_search_doc",
            label="Link tài liệu:",
            limit=5,
        )
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="drive_search_file",
            label="Link file tham khảo:",
            limit=5,
        )
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="drive_list_files",
            label="Link file gần đây:",
            limit=5,
        )
        final_text = _ensure_tool_links(
            final_text,
            messages,
            tools_called,
            tool_name="gmail_list_inbox",
            label="Link email:",
            limit=5,
        )
        return MiaChatResponse(
            final_text=final_text,
            tools_called=tools_called,
            thread_id=thread_id,
            request_id=request_id,
        )
