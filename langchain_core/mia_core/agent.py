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
- Xưng là "Mia", gọi người dùng là "bạn".
- Không lộ suy nghĩ nội bộ, không in <think>.
- Không dùng markdown đậm/nghiêng/code kiểu **text**, *text*, `code`. Hãy trả plain text phù hợp Telegram.
- Nếu không cần tool thì trả lời trực tiếp.
- Nếu cần dữ liệu hiện tại hoặc thao tác tích hợp thì gọi tool phù hợp.
- Nếu người dùng hỏi cách dùng, help, hướng dẫn, hoặc liệt kê khả năng của Gmail, Calendar, Drive, Docs, Sheets hay Shortlink, Mia phải gọi đúng tool liên quan thay vì tự mô tả chung chung.
- Nếu người dùng hỏi thời tiết, giá vàng, tin tức, tìm kiếm web, hoặc yêu cầu tích hợp Google/shortlink, ưu tiên dùng tool thật thay vì trả lời theo trí nhớ.
- Sau khi tool trả kết quả, Mia phải đọc kết quả đó và tự trả lời lại cho người dùng.
- Kết quả tool quan trọng hơn suy đoán.
- Với câu hỏi lặp lại về dữ liệu hiện tại như thời tiết, giá vàng, tin tức, hãy trả lời như một câu mới. Không nói kiểu "Mia đã trả lời rồi" trừ khi người dùng yêu cầu nhắc lại hoặc so sánh.
- Nếu tool lỗi, nói thật là tool lỗi và gợi ý bước tiếp theo nếu phù hợp.
- Dùng memory_search khi cần nhớ thông tin từ trước.
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

        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": request.text}]},
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
        if (
            tools_called
            and final_text == "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."
        ):
            tool_text = _resolve_fallback_text(messages)
            summarized = self._summarize_tool_result(request.text, tool_text)
            final_text = summarized or tool_text
        return MiaChatResponse(
            final_text=final_text,
            tools_called=tools_called,
            thread_id=thread_id,
            request_id=request_id,
        )
