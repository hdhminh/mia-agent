from __future__ import annotations

from typing import Any

from agent.graph.state import MiaGraphState
from agent.memory.repository import looks_like_durable_memory


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

    request = state.get("request")
    response = state.get("response")
    tools_called = state.get("tools_called", [])
    final_text = str(state.get("final_text") or "")
    created_proposals: list[dict[str, Any]] = []
    if (
        request is not None
        and response is not None
        and getattr(service.settings, "memory_proposals_enabled", True)
        and "memory_write" not in tools_called
        and looks_like_durable_memory(request.text)
    ):
        try:
            proposal = service.memory_repo.create_proposal(
                chat_id=request.chat_id,
                owner_id=request.resolved_user_id(),
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                content=request.text,
                memory_type="preference",
                memory_kind="semantic",
                title="User stated durable preference or fact",
                tags=["auto_proposal"],
                importance=3,
                confidence=0.68,
                source_text=request.text,
                evidence=[
                    {
                        "role": "user",
                        "text": request.text,
                        "request_id": request.resolved_request_id(),
                    }
                ],
                metadata={"source": "memory_writer_prefilter"},
            )
            if proposal:
                created_proposals.append(proposal)
        except Exception:
            created_proposals = []

    if created_proposals and response is not None:
        proposal_lines = []
        for proposal in created_proposals[:3]:
            proposal_lines.append(f"#{proposal.get('id')}: {proposal.get('content')}")
        suffix = (
            "\n\nMia thấy có thông tin có thể lưu vào memory nhưng đang chờ anh duyệt trước:\n"
            + "\n".join(proposal_lines)
            + "\nAnh có thể nhắn `duyệt memory #id` hoặc `bỏ memory #id`."
        )
        response.final_text = (response.final_text or final_text) + suffix
        final_text = response.final_text

    skill_request_id = state.get("skill_request_id", "")
    if skill_request_id and service.skill_engine is not None:
        skill_state = {"tools_called": state.get("tools_called", []), "final_text": final_text}
        approval_wait = any(cue in final_text.lower() for cue in ("xác nhận", "xac nhan", "confirmation", "confirm"))
        if approval_wait:
            service.skill_engine.repository.pause(request_id=skill_request_id, state=skill_state)
        else:
            service.skill_engine.repository.finish(
                request_id=skill_request_id,
                status="completed" if final_text else "failed",
                state=skill_state,
            )

    return {
        "memory_written": True,
        "memory_proposals": created_proposals,
        "final_text": final_text,
        "response": response,
    }
