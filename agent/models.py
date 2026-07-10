from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from agent.error_envelope import ErrorEnvelope


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
    ok: bool = True
    final_text: str
    tools_called: list[str] = Field(default_factory=list)
    thread_id: str
    request_id: str
    trace: dict[str, Any] = Field(default_factory=dict)
    error: ErrorEnvelope | None = None


class MiaFeedbackRequest(BaseModel):
    chat_id: str = Field(..., description="Telegram chat id or app conversation id.")
    request_id: str = Field(default="", description="Request id to attach feedback to.")
    thread_id: str = Field(default="", description="Conversation thread id.")
    source: str = Field(default="chat", description="Feedback source such as chat, media, or admin.")
    scope: str = Field(default="general", description="High-level scope such as general, document, image, media.")
    topic: str = Field(default="", description="Specific topic or tool name.")
    verdict: str = Field(default="", description="Feedback verdict such as up, down, shorter, longer, deeper, clearer.")
    rating: int = Field(default=0, ge=-1, le=1, description="Simple rating: -1, 0, 1.")
    comment: str = Field(default="", description="Short free-text feedback or correction.")
    correction_text: str = Field(default="", description="Optional corrected answer or preferred wording.")
    current_text: str = Field(default="", description="Current Mia answer being reviewed.")
    trace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MiaFeedbackResponse(BaseModel):
    ok: bool = True
    feedback_id: int | None = None
    insight_id: int | None = None
    message: str = ""
    error: ErrorEnvelope | None = None


class MiaAutomationRequest(BaseModel):
    chat_id: str
    user_id: str
    name: str = ""
    schedule: str = ""
    skill_name: str = ""
    input_text: str = ""
    next_run_at: str | None = None


class MiaAutomationActionRequest(BaseModel):
    chat_id: str
    user_id: str
    automation_id: int


class MiaMCPCallRequest(BaseModel):
    server: str
    tool: str = ""
    arguments: dict[str, Any] = Field(default_factory=dict)
