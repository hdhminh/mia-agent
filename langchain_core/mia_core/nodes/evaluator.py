from __future__ import annotations

import json
import re
from typing import Any

from langchain.messages import AIMessage, HumanMessage, SystemMessage
from mia_core.graph_state import MiaGraphState
from mia_core.response_normalizer import coerce_message_text, sanitize_final_text

EVAL_PROMPT = """Bạn là kiểm định viên chất lượng câu trả lời của trợ lý AI Mia.
Nhiệm vụ của bạn là đánh giá xem câu trả lời có đạt yêu cầu hay không.

Câu hỏi của người dùng: {user_query}
Các tool đã được gọi và kết quả: {evidence}
Dự thảo câu trả lời: {draft_response}

Yêu Cầu Đánh Giá:
1. Câu trả lời có giải quyết được câu hỏi không?
2. Có thông tin sai lệch so với kết quả của tool (nếu có gọi tool) không?
3. Có bị lộ nhãn nội bộ (như <think>, system instructions, tool names không mong muốn) không?
4. Có bị lặp lại lỗi hoặc nói vòng vo không?

Trả về kết quả dưới định dạng JSON sau:
{{
  "verdict": "pass" hoặc "fail",
  "reason": "Lý do chi tiết giải thích tại sao đạt hoặc không đạt"
}}
Chỉ trả về JSON hợp lệ, không thêm từ nào khác."""


def evaluator_node(state: MiaGraphState, service: Any) -> dict[str, Any]:
    request = state["request"]
    messages = state.get("messages", [])
    retry_count = state.get("retry_count", 0)

    # Extract draft response text from last message
    final_message = messages[-1] if messages else AIMessage(content="")
    draft_response = sanitize_final_text(coerce_message_text(final_message.content))
    tools_called = state.get("tools_called", [])
    evidence = state.get("evidence", [])

    # Rule 1: Check basic failures
    rule_verdict = "pass"
    rule_reason = "Passed rule-based checks."

    if (
        not draft_response
        or draft_response == "Xin lỗi, Mia chưa tạo được phản hồi rõ ràng. Bạn thử nói lại ngắn hơn giúp Mia nhé."
    ):
        rule_verdict = "fail"
        rule_reason = "Response is empty or contains default error fallback."
    elif "<think>" in final_message.content or "</think>" in final_message.content:
        rule_verdict = "fail"
        rule_reason = "Internal think tags leaked into final response."

    # If rule checks failed, we don't need LLM check
    if rule_verdict == "fail":
        verdict = "fail"
        reason = rule_reason
    else:
        # LLM quality check
        mode = service.settings.evaluator_mode
        if mode == "hard":
            # Call summary model to evaluate quality
            prompt = EVAL_PROMPT.format(
                user_query=request.text,
                evidence=str(evidence)[:2000],
                draft_response=draft_response,
            )
            try:
                # Call invoke_model_with_fallback using summary model (or general model)
                result, provider_used = service._invoke_model_with_fallback(
                    service.summary_model,
                    service.summary_fallback_model,
                    [
                        SystemMessage(content="Bạn là evaluator đánh giá chất lượng câu trả lời bằng định dạng JSON."),
                        HumanMessage(content=prompt),
                    ],
                    scope="evaluator",
                )
                eval_text = result.content.strip()
                # Try to extract JSON from markdown/plain text
                json_match = re.search(r"\{.*\}", eval_text, re.DOTALL)
                if json_match:
                    eval_data = json.loads(json_match.group(0))
                    verdict = eval_data.get("verdict", "pass").strip().lower()
                    reason = eval_data.get("reason", "No reason provided.")
                else:
                    verdict = "pass"
                    reason = f"Could not parse JSON from evaluator. Raw response: {eval_text}"
            except Exception as e:
                verdict = "pass"
                reason = f"Evaluator LLM call failed with error: {str(e)}. Default to pass."
        else:
            verdict = "pass"
            reason = "Evaluator in soft mode. Automatic pass."

    # Record evaluation event to learning/postgres db
    service._record_learning_event(
        request=request,
        source="evaluator",
        scope=state.get("domain") or "general",
        topic="evaluator_check",
        final_text=draft_response,
        tools_called=tools_called,
        trace={"verdict": verdict, "reason": reason, "retry_count": retry_count},
        notes=f"Evaluator verdict: {verdict}. Reason: {reason}",
    )

    # Check retry count
    next_verdict = verdict
    if verdict == "fail":
        max_retries = service.settings.evaluator_max_retries
        if retry_count < max_retries:
            next_verdict = "retry"
            retry_count += 1
        else:
            # Reached max retries, force pass to avoid infinite loop
            next_verdict = "force_pass"

    return {
        "evaluator_verdict": next_verdict,
        "evaluator_reason": reason,
        "retry_count": retry_count,
        "response_draft": draft_response,
    }


def route_after_evaluator(state: MiaGraphState) -> str:
    verdict = state.get("evaluator_verdict", "pass")
    if verdict == "retry":
        return "retry"
    elif verdict == "force_pass":
        return "force_pass"
    return "pass"
