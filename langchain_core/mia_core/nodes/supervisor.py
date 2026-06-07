from __future__ import annotations

from typing import Any

from mia_core.graph_state import MiaGraphState
from mia_core.prompts import DOMAIN_GUIDANCE


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
                "content": f"Lượt chạy trước không đạt yêu cầu với lý do: {state['evaluator_reason']}. Hãy điều chỉnh câu trả lời hoặc gọi tool chính xác hơn.",
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
                "content": f"Tool gợi ý gần nhất là {hint_tool}, nhưng chỉ dùng nếu thật sự khớp với ý định của người dùng.",
            }
        )
    if request.metadata:
        messages_payload.append(
            {
                "role": "system",
                "content": f"Attachment metadata: {request.metadata}",
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
    messages_payload.append(
        {
            "role": "system",
            "content": (
                "Chỉ xử lý yêu cầu mới nhất trong lượt này. "
                "Nếu không có chỉ dẫn tiếp tục rõ ràng, bỏ qua chủ đề và kết quả của lượt trước."
            ),
        }
    )
    messages_payload.append({"role": "user", "content": request.text})

    return {
        "messages": messages_payload,
        "learning_scopes": scopes,
        "agent_key": agent_key,
    }


def route_to_specialist(state: MiaGraphState) -> str:
    agent_key = state.get("agent_key") or "general"
    if agent_key in {"github", "calendar", "gmail", "workspace", "google_full", "media", "general"}:
        return agent_key
    return "general"
