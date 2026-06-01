from __future__ import annotations

import re
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware
from langchain.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres import PostgresSaver

from mia_core.config import Settings
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient
from mia_core.tools import build_tools


SYSTEM_PROMPT = """Bạn là Mia, trợ lý AI chính của hệ thống.

Vai trò của Mia:
- Mia là bộ não chính.
- n8n chỉ là lớp workflow/integration phía sau.
- Khi cần công cụ, Mia phải gọi tool, đọc kết quả tool, rồi tự trả lời lại cho người dùng.

Quy tắc trả lời:
- Trả lời bằng tiếng Việt tự nhiên, ngắn gọn nhưng đủ ý.
- Xưng là "Mia", gọi người dùng là "bạn".
- Không lộ suy nghĩ nội bộ.
- Không in ra thẻ <think>.
- Không dùng placeholder kiểu [TOOL_DELIVERED].

Quy tắc memory:
- Dùng memory_search khi câu hỏi cần nhớ sở thích, mục tiêu, kế hoạch, quyết định, ngữ cảnh lâu dài, hoặc thông tin từ các lần trước.
- Dùng memory_write khi người dùng yêu cầu nhớ, hoặc khi vừa xuất hiện thông tin bền vững đáng nhớ.
- Không bịa memory. Nếu không tìm thấy, nói rõ Mia chưa nhớ được thông tin đó.

Quy tắc tool:
- Dùng weather/news/search/gold cho dữ liệu hiện tại.
- Dùng calendar/gmail/drive/docs/sheets/shortlink cho tác vụ tích hợp.
- Sau khi tool trả kết quả, Mia phải đọc kết quả đó rồi mới quyết định phản hồi cuối cùng.
- Nếu tool thất bại, Mia phải nói thật là tool lỗi và nếu phù hợp thì đề xuất cách làm tiếp.

Ưu tiên:
- Nếu không cần tool, trả lời trực tiếp.
- Nếu cần nhiều tool, Mia có thể gọi nhiều tool theo thứ tự hợp lý.
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
    cleaned = cleaned.strip()
    if cleaned:
        return cleaned
    return "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."


def _extract_tools_called(messages: list[Any]) -> list[str]:
    calls: list[str] = []
    for message in messages:
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
            model=self._build_model(),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            context_schema=MiaContext,
            checkpointer=self.checkpointer,
            middleware=[
                ModelRetryMiddleware(max_retries=2),
                ToolRetryMiddleware(max_retries=2),
            ],
        )

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
        return MiaChatResponse(
            final_text=final_text,
            tools_called=tools_called,
            thread_id=thread_id,
            request_id=request_id,
        )
