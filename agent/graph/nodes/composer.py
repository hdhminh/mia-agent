from __future__ import annotations

from typing import Any

from langchain.messages import AIMessage
from agent.brain.direct_executor import build_memory_recent_text
from agent.graph.state import MiaGraphState
from agent.models import MiaChatResponse
from agent.i18n import t
from agent.brain.response_normalizer import (
    cap_visible_links as normalized_cap_visible_links,
    coerce_message_text as normalized_coerce_message_text,
    ensure_tool_links as normalized_ensure_tool_links,
    extract_tools_called as normalized_extract_tools_called,
    prefer_docs_search_output as normalized_prefer_docs_search_output,
    prefer_tool_truth as normalized_prefer_tool_truth,
    resolve_fallback_text as normalized_resolve_fallback_text,
    sanitize_final_text as normalized_sanitize_final_text,
)


def response_composer_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    request = state["request"]
    messages = state.get("messages", [])
    agent_key = state.get("agent_key") or "general"
    hint_tool = state.get("hint_tool", "")
    provider_used = state.get("provider_used", "primary")
    thread_id = state["thread_id"]
    request_id = state["request_id"]

    final_message = messages[-1] if messages else AIMessage(content="")
    final_text = normalized_sanitize_final_text(normalized_coerce_message_text(final_message.content))
    tools_called = normalized_extract_tools_called(messages)

    if not tools_called and hint_tool == "memory_recent":
        final_text = build_memory_recent_text(service.memory_repo, request.chat_id)
        tools_called = ["memory_recent"]

    if (
        tools_called
        and final_text == t("error.fallback_response")
    ):
        tool_text = normalized_resolve_fallback_text(messages)
        summarized, summary_trace = service._summarize_tool_result(request.text, tool_text)
        final_text = summarized or tool_text
    else:
        summary_trace = {}

    final_text = normalized_prefer_docs_search_output(request.text, final_text, messages, tools_called)
    final_text = normalized_prefer_tool_truth(final_text, messages, tools_called)

    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="search_web",
        label=t("composer.reference_link_label"),
        limit=3,
    )
    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="news_get",
        label=t("composer.reference_link_label"),
        limit=3,
    )
    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="docs_search_doc",
        label=t("composer.doc_link_label"),
        limit=3,
    )
    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="drive_search_file",
        label=t("composer.file_link_label"),
        limit=3,
    )
    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="drive_list_files",
        label=t("composer.recent_file_link_label"),
        limit=3,
    )
    final_text = normalized_ensure_tool_links(
        final_text,
        messages,
        tools_called,
        tool_name="gmail_list_inbox",
        label=t("composer.email_link_label"),
        limit=3,
    )
    final_text = normalized_cap_visible_links(final_text, limit=3)

    trace = dict(state.get("trace") or {})
    trace.update({
        "llm": service._cache_trace(final_message, scope=f"agent:{agent_key}", provider_used=provider_used),
        "provider": provider_used,
    })
    if summary_trace:
        trace["tool_summary"] = summary_trace

    response = MiaChatResponse(
        final_text=final_text,
        tools_called=tools_called,
        thread_id=thread_id,
        request_id=request_id,
        trace=trace,
    )

    return {
        "final_text": final_text,
        "tools_called": tools_called,
        "trace": trace,
        "response": response,
    }
