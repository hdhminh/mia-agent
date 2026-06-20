from __future__ import annotations

from typing import Any

from agent.graph.state import MiaGraphState
from agent.brain.response_normalizer import all_tool_messages, extract_tools_called


def make_specialist_node(agent_key: str):
    def specialist_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
        thread_id = state["thread_id"]
        context = state["context"]
        messages_payload = state["messages"]

        result, provider_used = service._invoke_agent_with_fallback(
            agent_key=agent_key,
            messages_payload=messages_payload,
            thread_id=thread_id,
            context=context,
        )

        messages = list(result.get("messages", []))
        tools_called = extract_tools_called(messages)
        evidence = all_tool_messages(messages)

        return {
            "messages": messages,
            "tools_called": tools_called,
            "evidence": evidence,
            "provider_used": provider_used,
        }
    return specialist_node
