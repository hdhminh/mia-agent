from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mia_core.error_envelope import ErrorEnvelope


class MediaRequest(BaseModel):
    tool: str = Field(..., min_length=1)
    request_id: str = Field(default="")
    chat_id: str = Field(default="")
    text: str = Field(default="")
    question: str = Field(default="")
    file_base64: str = Field(default="")
    file_name: str = Field(default="")
    mime_type: str = Field(default="")
    attachment_kind: str = Field(default="")
    has_attachment: bool = Field(default=False)
    language: str = Field(default="")
    voice: str = Field(default="")
    model: str = Field(default="")
    response_mode: str = Field(default="audio")
    prompt: str = Field(default="")
    max_chars: int = Field(default=0, ge=0)


class MediaResult(BaseModel):
    ok: bool = True
    tool: str
    text: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    file_name: str = ""
    mime_type: str = ""
    attachment_kind: str = ""
    warnings: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
    error: ErrorEnvelope | None = None


class MediaTextResult(MediaResult):
    pass
