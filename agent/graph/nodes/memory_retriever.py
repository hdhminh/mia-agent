from __future__ import annotations

from time import perf_counter
from typing import Any

from agent.brain.planner import normalize_query_text
from agent.graph.state import MiaGraphState
from agent.memory.repository import build_memory_context


LOW_SIGNAL_TEXTS = {
    "hi",
    "hello",
    "xin chao",
    "xin chào",
    "ok",
    "oke",
    "ừ",
    "uh",
    "test",
}


def should_retrieve_memory(text: str) -> bool:
    normalized = normalize_query_text(text)
    if not normalized or normalized in LOW_SIGNAL_TEXTS:
        return False
    if len(normalized) < 8:
        return False
    return True


def memory_retriever_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    request = state["request"]
    context = state["context"]
    settings = service.settings
    if not getattr(settings, "memory_rag_enabled", True):
        return {"retrieved_memories": [], "memory_context": ""}
    if not should_retrieve_memory(request.text):
        return {"retrieved_memories": [], "memory_context": ""}

    started = perf_counter()
    try:
        rows = service.memory_repo.search(
            chat_id=request.chat_id,
            owner_id=context.user_id,
            query=request.text,
            limit=max(1, min(int(settings.memory_rag_limit), 8)),
            threshold=max(0.0, min(float(settings.memory_rag_threshold), 1.0)),
        )
    except Exception as exc:
        trace = dict(state.get("trace") or {})
        trace["memory_rag"] = {
            "ok": False,
            "error": str(exc),
            "latency_ms": round((perf_counter() - started) * 1000, 2),
        }
        return {"retrieved_memories": [], "memory_context": "", "trace": trace}

    memory_context = build_memory_context(
        rows,
        token_budget=max(200, int(settings.memory_rag_token_budget)),
    )
    trace = dict(state.get("trace") or {})
    trace["memory_rag"] = {
        "ok": True,
        "retrieved": len(rows),
        "context_chars": len(memory_context),
        "latency_ms": round((perf_counter() - started) * 1000, 2),
    }
    return {
        "retrieved_memories": rows,
        "memory_context": memory_context,
        "trace": trace,
    }
