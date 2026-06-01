from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class MiaContext:
    chat_id: str
    user_id: str
    timezone: str
    request_id: str


class MiaChatRequest(BaseModel):
    chat_id: str = Field(..., description="Telegram chat id or app conversation id.")
    text: str = Field(..., min_length=1, description="Latest user message.")
    thread_id: str | None = Field(
        default=None,
        description="Conversation thread id for LangGraph checkpoints.",
    )
    user_id: str | None = Field(default=None, description="Stable user id.")
    metadata: dict[str, Any] = Field(default_factory=dict)

    def resolved_thread_id(self) -> str:
        return self.thread_id or f"telegram:{self.chat_id}"

    def resolved_user_id(self) -> str:
        return self.user_id or self.chat_id

    def resolved_request_id(self) -> str:
        return str(self.metadata.get("request_id") or uuid4())


class MiaChatResponse(BaseModel):
    final_text: str
    tools_called: list[str] = Field(default_factory=list)
    thread_id: str
    request_id: str
