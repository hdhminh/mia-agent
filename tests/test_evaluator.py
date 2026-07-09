from __future__ import annotations

import unittest
from dataclasses import dataclass

from langchain.messages import AIMessage, HumanMessage

from agent.brain.router import RouteDecision
from agent.graph.nodes.evaluator import evaluator_node
from agent.models import MiaChatRequest


@dataclass
class _DummySettings:
    evaluator_mode: str = "soft"
    evaluator_max_retries: int = 2


class _DummyService:
    def __init__(self) -> None:
        self.settings = _DummySettings()
        self.records: list[dict[str, object]] = []

    def _record_learning_event(self, **kwargs: object) -> None:
        self.records.append(dict(kwargs))

    def _invoke_model_with_fallback(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - safety net
        raise AssertionError("LLM evaluator should not run in these tests")


def _build_state(
    *,
    request_text: str,
    domain: str,
    agent_key: str,
    hint_tool: str,
    tools_called: list[str],
    evidence: list[str],
) -> dict[str, object]:
    request = MiaChatRequest(chat_id="chat-1", text=request_text)
    route = RouteDecision(
        route_type="agentic_domain",
        domain=domain,
        hint_tool=hint_tool,
        agent_key=agent_key,
        direct_confident=False,
        reason="test",
    )
    return {
        "request": request,
        "route": route,
        "domain": domain,
        "agent_key": agent_key,
        "hint_tool": hint_tool,
        "messages": [
            HumanMessage(content=request_text),
            AIMessage(content="Mia đã tổng hợp kết quả."),
        ],
        "tools_called": tools_called,
        "evidence": evidence,
        "retry_count": 0,
    }


class EvaluatorToolEvidenceTests(unittest.TestCase):
    def test_github_response_without_tool_evidence_fails_fast(self) -> None:
        service = _DummyService()
        state = _build_state(
            request_text="xem repo github example/repo",
            domain="github",
            agent_key="github",
            hint_tool="github_get_repo",
            tools_called=[],
            evidence=[],
        )

        result = evaluator_node(state, service)

        self.assertEqual(result["evaluator_verdict"], "retry")
        self.assertIn("GitHub response has no tool evidence", result["evaluator_reason"])
        self.assertEqual(service.records[0]["trace"]["verdict"], "fail")

    def test_web_response_without_tool_evidence_fails_fast(self) -> None:
        service = _DummyService()
        state = _build_state(
            request_text="tóm tắt link này https://example.com/article",
            domain="general",
            agent_key="general",
            hint_tool="summarize_url",
            tools_called=[],
            evidence=[],
        )

        result = evaluator_node(state, service)

        self.assertEqual(result["evaluator_verdict"], "retry")
        self.assertIn("Web response has no tool evidence", result["evaluator_reason"])
        self.assertEqual(service.records[0]["trace"]["verdict"], "fail")

    def test_tool_backed_response_passes(self) -> None:
        service = _DummyService()
        state = _build_state(
            request_text="xem repo github example/repo",
            domain="github",
            agent_key="github",
            hint_tool="github_get_repo",
            tools_called=["github_get_repo"],
            evidence=["Repo info"],
        )

        result = evaluator_node(state, service)

        self.assertEqual(result["evaluator_verdict"], "pass")
        self.assertEqual(result["evaluator_reason"], "Evaluator in soft mode. Automatic pass.")
        self.assertEqual(service.records[0]["trace"]["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
