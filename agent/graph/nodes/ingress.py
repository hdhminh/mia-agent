from __future__ import annotations

from typing import Any

from agent.skills import registry as caps
from agent.graph.state import MiaGraphState
from agent.models import MiaChatResponse
from agent.brain.router import route_request


def ingress_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    request = state["request"]
    context = state["context"]
    thread_id = state["thread_id"]
    request_id = state["request_id"]

    # 1. Approval check
    approval_response = service._try_pending_action_confirmation(request, context)
    if approval_response is not None:
        return {"response": approval_response}

    # 2. GitHub search followup
    github_followup_response = service._try_github_search_followup(request)
    if github_followup_response is not None:
        return {"response": github_followup_response}

    # 3. GitHub selected repo followup
    github_repo_followup_response = service._try_github_selected_repo_followup(request, context)
    if github_repo_followup_response is not None:
        return {"response": github_repo_followup_response}

    # 4. Route request
    route = route_request(request.text, request.metadata)
    clarify_text = service._maybe_clarify_request(request, route)
    if clarify_text:
        response = MiaChatResponse(
            final_text=clarify_text,
            tools_called=[],
            thread_id=thread_id,
            request_id=request_id,
            trace={},
        )
        service._record_learning_event(
            request=request,
            source="clarify",
            scope=route.domain or "general",
            topic="clarify_multi_google",
            final_text=response.final_text,
            tools_called=[],
            trace={},
            notes="clarification requested for multi-google ambiguity",
        )
        return {"response": response, "route": route}

    hint_tool = route.hint_tool

    # 5. Capabilities overview
    if hint_tool == "__capabilities_overview__":
        response = MiaChatResponse(
            final_text=caps.build_capability_overview_text(),
            tools_called=[],
            thread_id=thread_id,
            request_id=request_id,
            trace={},
        )
        service._record_learning_event(
            request=request,
            source="direct",
            scope="general",
            topic="capabilities_overview",
            final_text=response.final_text,
            tools_called=[],
            trace={},
            notes="capability overview request",
        )
        return {"response": response, "route": route, "hint_tool": hint_tool}

    # 6. Direct executor
    direct_response = service._try_direct_route(request, context, hint_tool)
    if direct_response is not None:
        service._record_learning_event(
            request=request,
            source="direct",
            scope=route.domain or route.agent_key or "general",
            topic=hint_tool,
            final_text=direct_response.final_text,
            tools_called=direct_response.tools_called,
            trace=direct_response.trace,
            notes="direct route response",
        )
        return {"response": direct_response, "route": route, "hint_tool": hint_tool}

    # 7. URL memory followup
    url_followup_response = service._try_url_memory_followup(request)
    if url_followup_response is not None:
        return {"response": url_followup_response, "route": route, "hint_tool": hint_tool}

    # 8. Document memory followup
    document_followup_response = service._try_document_memory_followup(request)
    if document_followup_response is not None:
        return {"response": document_followup_response, "route": route, "hint_tool": hint_tool}

    # No fast path matches, proceed to supervisor/agents
    return {
        "response": None,
        "route": route,
        "hint_tool": hint_tool,
        "domain": route.domain,
        "agent_key": route.agent_key or "general",
    }


def route_after_ingress(state: MiaGraphState) -> str:
    if state.get("response") is not None:
        return "resolved"
    return "needs_specialist"
