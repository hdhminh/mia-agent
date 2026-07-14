from __future__ import annotations

from typing import Any

from agent.graph.state import MiaGraphState
from agent.persona.domain_guidance import DOMAIN_GUIDANCE
from agent.i18n import t


def supervisor_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    request = state["request"]
    route = state["route"]
    hint_tool = state.get("hint_tool", "")
    agent_key = state.get("agent_key") or "general"

    messages_payload: list[dict[str, str]] = []

    # If it is a retry, add system guidance based on evaluator verdict/reason
    if state.get("retry_count", 0) > 0 and state.get("evaluator_reason"):
        messages_payload.append(
            {
                "role": "system",
                "content": t("supervisor.evaluator_retry_hint", reason=state["evaluator_reason"]),
            }
        )

    if route.domain in DOMAIN_GUIDANCE:
        messages_payload.append(
            {
                "role": "system",
                "content": DOMAIN_GUIDANCE[route.domain],
            }
        )
    if hint_tool:
        messages_payload.append(
            {
                "role": "system",
                "content": t("supervisor.hint_tool_guidance", hint_tool=hint_tool),
            }
        )
    if request.metadata:
        messages_payload.append(
            {
                "role": "system",
                "content": f"Attachment metadata: {request.metadata}",
            }
        )
        active_project = request.metadata.get("active_code_project")
        if isinstance(active_project, dict) and active_project.get("project_id"):
            project_id = str(active_project.get("project_id") or "").strip()
            project_name = str(active_project.get("project_name") or project_id).strip()
            messages_payload.append(
                {
                    "role": "system",
                    "content": (
                        f"Code project hiện hành của người dùng là '{project_name}'"
                        f" (project_id: {project_id}). Nếu yêu cầu là chỉnh/sửa/thêm code tiếp theo,"
                        " hãy ưu tiên tiếp tục trên project này bằng tool code_work_on_project thay vì hỏi lại project."
                    ),
                }
            )
    scopes = service._learning_scopes(
        route_domain=route.domain,
        agent_key=agent_key,
        hint_tool=hint_tool,
    )
    learning_guidance = service._learning_guidance_text(scopes=scopes, limit=4)
    if learning_guidance:
        messages_payload.append(
            {
                "role": "system",
                "content": learning_guidance,
            }
        )
    skill_name = ""
    if service.skill_engine is not None:
        skill_name, skill_guidance = service.skill_engine.start_guidance(
            query=request.text,
            request_id=state["request_id"],
            chat_id=request.chat_id,
            user_id=request.resolved_user_id(),
        )
        if skill_guidance:
            messages_payload.append({"role": "system", "content": skill_guidance})
    messages_payload.append(
        {
            "role": "system",
            "content": t("supervisor.turn_focus_guidance"),
        }
    )
    messages_payload.append({"role": "user", "content": request.text})

    return {
        "messages": messages_payload,
        "learning_scopes": scopes,
        "agent_key": agent_key,
        "skill_name": skill_name,
        "skill_request_id": state["request_id"] if skill_name else "",
    }


def route_to_specialist(state: MiaGraphState) -> str:
    agent_key = state.get("agent_key") or "general"
    if agent_key in {"github", "maps", "smarthome", "code", "calendar", "gmail", "workspace", "google_full", "media", "general"}:
        return agent_key
    return "general"
