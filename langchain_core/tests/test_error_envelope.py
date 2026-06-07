from __future__ import annotations

import unittest
from dataclasses import dataclass

from mia_core.direct_executor import DirectExecutor
from mia_core.error_envelope import (
    ErrorEnvelope,
    build_approval_required_envelope,
    build_tool_http_error_envelope,
)
from mia_core.models import MiaChatRequest, MiaContext
from mia_core.n8n_client import N8nToolGatewayClient, ToolGatewayResult


class _DummyMemoryRepo:
    def write(self, **_: object) -> None:  # pragma: no cover - not used in error path
        return None


@dataclass
class _DummyErrorGateway:
    result: ToolGatewayResult

    def run_tool(
        self,
        tool_name: str,
        tool_args: dict[str, object],
        _context: MiaContext,
        *,
        request_text: str = "",
        force_execute: bool = False,
    ) -> ToolGatewayResult:
        self.last_call = {
            "tool_name": tool_name,
            "tool_args": dict(tool_args),
            "request_text": request_text,
            "force_execute": force_execute,
        }
        return self.result


class _DummyApprovalRepo:
    def __init__(self) -> None:
        self.pending_calls: list[dict[str, object]] = []

    def create_pending_action(self, **kwargs: object) -> dict[str, object]:
        self.pending_calls.append(dict(kwargs))
        return {
            "id": 99,
            "summary": "gửi email xác nhận",
            "gateway_name": str(kwargs.get("gateway_name") or kwargs.get("tool_name") or ""),
        }

    def mark_pending_action_status(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - not used
        return None


class ErrorEnvelopeTests(unittest.TestCase):
    def test_http_error_envelope_classifies_not_found(self) -> None:
        envelope = build_tool_http_error_envelope(
            tool_name="github.get_file",
            status_code=404,
            response_text="Not found",
            error_text="github.get_file failed: HTTP 404",
            request_id="req-1",
            chat_id="chat-1",
        )

        self.assertFalse(envelope.ok)
        self.assertEqual(envelope.code, "tool_not_found")
        self.assertEqual(envelope.category, "not_found")
        self.assertFalse(envelope.retryable)
        self.assertIn("không tìm thấy", envelope.display_text().lower())
        self.assertEqual(envelope.source.tool, "github.get_file")

    def test_approval_required_envelope_has_user_guidance(self) -> None:
        envelope = build_approval_required_envelope(
            tool_name="gmail.send_email",
            summary="gửi email xác nhận",
            pending_action_id=12,
            request_id="req-1",
            chat_id="chat-1",
        )

        self.assertEqual(envelope.code, "approval_required")
        self.assertEqual(envelope.category, "approval_required")
        self.assertFalse(envelope.retryable)
        self.assertIn("xác nhận", envelope.display_text().lower())
        self.assertEqual(envelope.details["pending_action_id"], 12)

    def test_envelope_serializes_inside_chat_response(self) -> None:
        envelope = ErrorEnvelope.build(
            code="tool_failed",
            category="external",
            severity="error",
            message="github.get_file failed.",
            user_message="Mình gặp lỗi từ tool gateway.",
            request_id="req-1",
            chat_id="chat-1",
        )

        response = envelope.model_dump(mode="json")
        self.assertEqual(response["code"], "tool_failed")
        self.assertEqual(response["user_message"], "Mình gặp lỗi từ tool gateway.")
        self.assertEqual(response["source"]["layer"], "unknown")

    def test_direct_executor_returns_error_response(self) -> None:
        envelope = build_tool_http_error_envelope(
            tool_name="web.read_url",
            status_code=404,
            response_text="Not found",
            error_text="web.read_url failed: HTTP 404",
            request_id="req-1",
            chat_id="chat-1",
        )
        gateway = _DummyErrorGateway(
            result=ToolGatewayResult(
                ok=False,
                tool="web.read_url",
                text=envelope.display_text(),
                payload={"ok": False, "error": envelope.model_dump(mode="json")},
                error=envelope,
            )
        )
        executor = DirectExecutor(memory_repo=_DummyMemoryRepo(), tool_gateway=gateway)  # type: ignore[arg-type]
        request = MiaChatRequest(chat_id="chat-1", text="đọc https://example.com")
        context = MiaContext(chat_id="chat-1", user_id="chat-1", timezone="Asia/Ho_Chi_Minh", request_id="req-1")

        response = executor.execute(request, context, "read_url", allow_multistep=True)

        self.assertIsNotNone(response)
        assert response is not None
        self.assertFalse(response.ok)
        self.assertIsNotNone(response.error)
        self.assertEqual(response.error.code, "tool_not_found")
        self.assertEqual(response.final_text, envelope.display_text())

    def test_tool_gateway_approval_branch_returns_error_envelope(self) -> None:
        approval_repo = _DummyApprovalRepo()
        gateway = N8nToolGatewayClient(
            url="http://example.invalid",
            token="token",
            timeout_seconds=1.0,
            approval_repo=approval_repo,
        )
        context = MiaContext(chat_id="chat-1", user_id="chat-1", timezone="Asia/Ho_Chi_Minh", request_id="req-1")

        result = gateway.run_tool(
            "gmail.send_email",
            {"to": "someone@example.com", "subject": "Test"},
            context,
            request_text="gửi email cho ai đó",
        )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "approval_required")
        self.assertEqual(result.payload["error"]["code"], "approval_required")
        self.assertEqual(approval_repo.pending_calls[0]["tool_name"], "gmail.send_email")


if __name__ == "__main__":
    unittest.main()
