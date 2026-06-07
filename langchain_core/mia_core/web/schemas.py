from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mia_core.error_envelope import ErrorEnvelope


class WebRequest(BaseModel):
    tool: str = Field(..., min_length=1)
    request_id: str = Field(default="")
    chat_id: str = Field(default="")
    url: str = Field(default="")
    text: str = Field(default="")
    prompt: str = Field(default="")
    instruction: str = Field(default="")
    question: str = Field(default="")
    response_mode: str = Field(default="text")
    max_chars: int = Field(default=0, ge=0)


class WebResult(BaseModel):
    ok: bool = True
    tool: str
    url: str = ""
    final_url: str = ""
    title: str = ""
    canonical_url: str = ""
    text: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
    error: ErrorEnvelope | None = None
