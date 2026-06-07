from __future__ import annotations

from typing import Any, TypedDict

from mia_core.models import MiaChatRequest, MiaChatResponse, MiaContext
from mia_core.router import RouteDecision


class MiaGraphState(TypedDict, total=False):
    # Input
    request: MiaChatRequest
    context: MiaContext
    thread_id: str
    request_id: str

    # Router
    route: RouteDecision
    hint_tool: str
    domain: str
    agent_key: str          # "github" | "google" | "media" | "general" | "google_full" etc.

    # Specialist inputs/outputs
    messages: list[Any]
    evidence: list[str]
    tools_called: list[str]

    # Evaluator
    evaluator_verdict: str  # "pass" | "fail" | "clarify"
    evaluator_reason: str
    retry_count: int

    # Response
    response_draft: str
    final_text: str
    response: MiaChatResponse | None

    # Memory
    pending_memory_writes: list[dict[str, Any]]
    memory_written: bool

    # Trace
    provider_used: str
    trace: dict[str, Any]
    learning_scopes: list[str]
