from __future__ import annotations

from typing import Any

from agent.graph.state import MiaGraphState


def memory_writer_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    # If the response was resolved through fast-path (no specialist run), we don't log "agent" learning event again.
    if state.get("final_text") and state.get("agent_key"):
        request = state["request"]
        agent_key = state.get("agent_key") or "general"
        tools_called = state.get("tools_called", [])
        final_text = state.get("final_text", "")
        trace = state.get("trace", {})

        service._record_learning_event(
            request=request,
            source="agent",
            scope=state.get("domain") or agent_key or "general",
            topic=state.get("hint_tool") or (tools_called[0] if tools_called else ""),
            final_text=final_text,
            tools_called=tools_called,
            trace=trace,
            notes="agent response",
        )

    return {"memory_written": True}
