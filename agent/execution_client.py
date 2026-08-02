from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from agent.approval import ApprovalRepository, DANGEROUS_GATEWAY_NAMES, should_require_confirmation
from agent.execution_journal import ExecutionJournalRepository, build_idempotency_key
from agent.i18n import t
from agent.error_envelope import (
    ErrorEnvelope,
    ErrorSource,
    build_approval_required_envelope,
    build_tool_http_error_envelope,
    build_tool_result_error_envelope,
    build_tool_transport_error_envelope,
)
from agent.learning.repository import LearningRepository
from agent.models import MiaContext


@dataclass(frozen=True)
class ToolGatewayResult:
    ok: bool
    tool: str
    text: str
    payload: dict[str, Any]
    error: ErrorEnvelope | None = None


class N8nToolGatewayClient:
    def __init__(
        self,
        url: str,
        token: str,
        timeout_seconds: float,
        *,
        learning_repo: LearningRepository | None = None,
        approval_repo: ApprovalRepository | None = None,
        execution_journal: ExecutionJournalRepository | None = None,
        code_runner_client: Any | None = None,
    ) -> None:
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.learning_repo = learning_repo
        self.approval_repo = approval_repo
        self.execution_journal = execution_journal
        self.code_runner_client = code_runner_client

    @staticmethod
    def _scope_from_gateway_name(gateway_name: str) -> str:
        clean = str(gateway_name or "").strip()
        if "." in clean:
            return clean.split(".", 1)[0] or "general"
        return clean or "general"

    @staticmethod
    def _extract_trace(payload: dict[str, Any] | None) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return {}
        trace = payload.get("trace")
        if isinstance(trace, dict):
            return trace
        data = payload.get("data")
        if isinstance(data, dict):
            nested = data.get("trace")
            if isinstance(nested, dict):
                return nested
        return {}

    @staticmethod
    def _default_error_source(tool_name: str, *, component: str) -> ErrorSource:
        return ErrorSource(
            layer="tool_gateway",
            component=component,
            operation="run_tool",
            tool=tool_name,
            workflow="Mia: Tool Gateway",
        )

    def _record_gateway_event(
        self,
        *,
        gateway_name: str,
        context: MiaContext,
        request_text: str,
        result_text: str,
        issue_type: str,
        latency_ms: float,
        ok: bool,
        payload: dict[str, Any] | None = None,
        error_text: str = "",
        metadata_extra: dict[str, Any] | None = None,
    ) -> None:
        if not self.learning_repo:
            return
        metadata = {
            "gateway_name": gateway_name,
            "latency_ms": round(max(0.0, float(latency_ms)), 1),
            "ok": bool(ok),
            "issue_type": issue_type,
            "status_code": int(payload.get("status_code") or 0) if isinstance(payload, dict) else 0,
            "error": error_text,
        }
        error_payload = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error_payload, dict):
            metadata["error_code"] = str(error_payload.get("code") or "")
            metadata["error_category"] = str(error_payload.get("category") or "")
            metadata["error_retryable"] = bool(error_payload.get("retryable"))
        if metadata_extra:
            metadata.update(metadata_extra)
        try:
            self.learning_repo.record_event(
                chat_id=context.chat_id,
                request_id=context.request_id,
                source="n8n_tool",
                scope=self._scope_from_gateway_name(gateway_name),
                topic=gateway_name,
                user_text=request_text,
                final_text=result_text,
                tools_called=[gateway_name],
                trace=self._extract_trace(payload),
                issue_type=issue_type,
                severity=1 if issue_type == "tool_fail" else 0,
                metadata=metadata,
                notes=f"gateway={gateway_name}",
            )
        except Exception:
            pass

    def run_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: MiaContext,
        *,
        request_text: str = "",
        force_execute: bool = False,
    ) -> ToolGatewayResult:
        if (
            self.approval_repo is not None
            and not force_execute
            and should_require_confirmation(tool_name, args, request_text)
        ):
            pending = self.approval_repo.create_pending_action(
                chat_id=context.chat_id,
                user_id=context.user_id,
                request_id=context.request_id,
                tool_name=tool_name,
                gateway_name=tool_name,
                args=args,
                reason="dangerous tool action requires explicit confirmation",
            )
            summary = str(pending.get("summary") or tool_name).strip()
            confirm_keyword = t("error.approval_confirm_keyword")
            text = t(
                "error.approval_required",
                summary=summary,
                confirm_keyword=confirm_keyword,
            )
            payload = {
                "ok": False,
                "status": "approval_required",
                "pending_action": pending,
                "trace": {},
            }
            envelope = build_approval_required_envelope(
                tool_name=tool_name,
                summary=summary,
                pending_action_id=int(pending.get("id") or 0) or None,
                request_id=context.request_id,
                thread_id="",
                chat_id=context.chat_id,
                source=self._default_error_source(tool_name, component="approval"),
            )
            payload["error"] = envelope.model_dump(mode="json")
            self._record_gateway_event(
                gateway_name=tool_name,
                context=context,
                request_text=request_text,
                result_text=envelope.display_text(),
                issue_type="approval_required",
                latency_ms=0.0,
                ok=False,
                payload=payload,
                metadata_extra={"pending_action_id": pending.get("id")},
            )
            return ToolGatewayResult(ok=False, tool=tool_name, text=envelope.display_text(), payload=payload, error=envelope)

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["x-mia-tool-token"] = self.token

        payload = {
            "tool": tool_name,
            "args": args,
            "chatId": context.chat_id,
            "userId": context.user_id,
            "requestId": context.request_id,
            "deliveryMode": "return",
        }
        if request_text.strip():
            payload["text"] = request_text.strip()
            payload["rawText"] = request_text.strip()

        journal_key = ""
        if self.execution_journal is not None and tool_name in DANGEROUS_GATEWAY_NAMES:
            journal_key = build_idempotency_key(
                user_id=context.user_id,
                request_id=context.request_id,
                tool_name=tool_name,
                args=args,
            )
            created, existing = self.execution_journal.reserve(
                idempotency_key=journal_key,
                request_id=context.request_id,
                chat_id=context.chat_id,
                user_id=context.user_id,
                tool_name=tool_name,
                args=args,
            )
            if not created:
                status = str(existing.get("status") or "").strip()
                cached = existing.get("result") if isinstance(existing.get("result"), dict) else {}
                if status == "completed" and cached:
                    return ToolGatewayResult(
                        ok=bool(cached.get("ok", True)),
                        tool=tool_name,
                        text=str(cached.get("text") or "").strip(),
                        payload={**cached, "idempotency_replay": True, "idempotency_key": journal_key},
                    )
                envelope = ErrorEnvelope.build(
                    code="duplicate_action_in_progress",
                    category="conflict",
                    severity="warn",
                    message=f"Duplicate execution blocked for {tool_name}.",
                    user_message="Thao tác này đang được xử lý hoặc đã được ghi nhận. Mia sẽ không chạy lặp lại.",
                    retryable=False,
                    request_id=context.request_id,
                    chat_id=context.chat_id,
                    details={"tool_name": tool_name, "idempotency_key": journal_key, "status": status},
                )
                return ToolGatewayResult(
                    ok=False,
                    tool=tool_name,
                    text=envelope.display_text(),
                    payload={"ok": False, "error": envelope.model_dump(mode="json"), "idempotency_key": journal_key},
                    error=envelope,
                )

        start = time.monotonic()
        status_code = 0
        response_text = ""
        with httpx.Client(timeout=self.timeout_seconds) as client:
            try:
                response = client.post(self.url, headers=headers, json=payload)
                status_code = response.status_code
                response_text = response.text or ""
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException as exc:
                latency_ms = (time.monotonic() - start) * 1000.0
                error_text = str(exc)
                envelope = build_tool_transport_error_envelope(
                    tool_name=tool_name,
                    error_text=error_text,
                    timeout=True,
                    request_id=context.request_id,
                    thread_id="",
                    chat_id=context.chat_id,
                    source=self._default_error_source(tool_name, component="timeout"),
                )
                payload = {
                    "status_code": status_code,
                    "response_text": response_text,
                    "error": envelope.model_dump(mode="json"),
                    "ok": False,
                }
                self._record_gateway_event(
                    gateway_name=tool_name,
                    context=context,
                    request_text=request_text,
                    result_text=envelope.display_text(),
                    issue_type="tool_fail",
                    latency_ms=latency_ms,
                    ok=False,
                    payload=payload,
                    error_text=error_text,
                )
                if journal_key and self.execution_journal:
                    self.execution_journal.finish(idempotency_key=journal_key, status="failed", result=payload, error_text=error_text)
                return ToolGatewayResult(
                    ok=False,
                    tool=tool_name,
                    text=envelope.display_text(),
                    payload=payload,
                    error=envelope,
                )
            except httpx.RequestError as exc:
                latency_ms = (time.monotonic() - start) * 1000.0
                error_text = str(exc)
                envelope = build_tool_transport_error_envelope(
                    tool_name=tool_name,
                    error_text=error_text,
                    timeout=False,
                    request_id=context.request_id,
                    thread_id="",
                    chat_id=context.chat_id,
                    source=self._default_error_source(tool_name, component="transport"),
                )
                payload = {
                    "status_code": status_code,
                    "response_text": response_text,
                    "error": envelope.model_dump(mode="json"),
                    "ok": False,
                }
                self._record_gateway_event(
                    gateway_name=tool_name,
                    context=context,
                    request_text=request_text,
                    result_text=envelope.display_text(),
                    issue_type="tool_fail",
                    latency_ms=latency_ms,
                    ok=False,
                    payload=payload,
                    error_text=error_text,
                )
                if journal_key and self.execution_journal:
                    self.execution_journal.finish(idempotency_key=journal_key, status="failed", result=payload, error_text=error_text)
                return ToolGatewayResult(
                    ok=False,
                    tool=tool_name,
                    text=envelope.display_text(),
                    payload=payload,
                    error=envelope,
                )
            except httpx.HTTPStatusError as exc:
                latency_ms = (time.monotonic() - start) * 1000.0
                response = exc.response
                status_code = response.status_code if response is not None else status_code
                response_text = response.text if response is not None else response_text
                error_text = str(exc)
                envelope = build_tool_http_error_envelope(
                    tool_name=tool_name,
                    status_code=status_code,
                    response_text=response_text,
                    error_text=error_text,
                    request_id=context.request_id,
                    thread_id="",
                    chat_id=context.chat_id,
                    source=self._default_error_source(tool_name, component="http_status"),
                )
                payload = {
                    "status_code": status_code,
                    "response_text": response_text,
                    "error": envelope.model_dump(mode="json"),
                    "ok": False,
                }
                self._record_gateway_event(
                    gateway_name=tool_name,
                    context=context,
                    request_text=request_text,
                    result_text=envelope.display_text(),
                    issue_type="tool_fail",
                    latency_ms=latency_ms,
                    ok=False,
                    payload=payload,
                    error_text=error_text,
                )
                if journal_key and self.execution_journal:
                    self.execution_journal.finish(idempotency_key=journal_key, status="failed", result=payload, error_text=error_text)
                return ToolGatewayResult(
                    ok=False,
                    tool=tool_name,
                    text=envelope.display_text(),
                    payload=payload,
                    error=envelope,
                )
            except ValueError as exc:
                latency_ms = (time.monotonic() - start) * 1000.0
                error_text = str(exc)
                envelope = build_tool_transport_error_envelope(
                    tool_name=tool_name,
                    error_text=error_text,
                    timeout=False,
                    request_id=context.request_id,
                    thread_id="",
                    chat_id=context.chat_id,
                    source=self._default_error_source(tool_name, component="response_parse"),
                )
                payload = {
                    "status_code": status_code,
                    "response_text": response_text,
                    "error": envelope.model_dump(mode="json"),
                    "ok": False,
                }
                self._record_gateway_event(
                    gateway_name=tool_name,
                    context=context,
                    request_text=request_text,
                    result_text=envelope.display_text(),
                    issue_type="tool_fail",
                    latency_ms=latency_ms,
                    ok=False,
                    payload=payload,
                    error_text=error_text,
                )
                if journal_key and self.execution_journal:
                    self.execution_journal.finish(idempotency_key=journal_key, status="failed", result=payload, error_text=error_text)
                return ToolGatewayResult(
                    ok=False,
                    tool=tool_name,
                    text=envelope.display_text(),
                    payload=payload,
                    error=envelope,
                )

        ok = bool(data.get("ok", False))
        text = str(data.get("text") or data.get("result") or "").strip()
        latency_ms = (time.monotonic() - start) * 1000.0
        issue_type = "tool_success" if ok else "tool_fail"
        envelope = None
        if not ok:
            envelope = build_tool_result_error_envelope(
                tool_name=tool_name,
                error_text=str(data.get("error") or f"{tool_name} failed."),
                response_text=text,
                status_text=str(data.get("status") or data.get("code") or ""),
                status_code=status_code or None,
                retryable=bool(data.get("retryable") or data.get("canRetry")),
                request_id=context.request_id,
                thread_id="",
                chat_id=context.chat_id,
                source=self._default_error_source(tool_name, component="tool_result"),
            )
            text = envelope.display_text()
            data = dict(data)
            data["error"] = envelope.model_dump(mode="json")
        self._record_gateway_event(
            gateway_name=tool_name,
            context=context,
            request_text=request_text,
            result_text=text or response_text,
            issue_type=issue_type,
            latency_ms=latency_ms,
            ok=ok,
            payload=data,
        )
        if journal_key and self.execution_journal:
            self.execution_journal.finish(
                idempotency_key=journal_key,
                status="completed" if ok else "failed",
                result=data,
                error_text="" if ok else text,
            )
        return ToolGatewayResult(ok=ok, tool=tool_name, text=text, payload=data, error=envelope)

    def run_pending_action(
        self,
        pending_action: dict[str, Any],
        context: MiaContext,
        *,
        request_text: str = "",
    ) -> ToolGatewayResult:
        action_id = int(pending_action.get("id") or 0)
        gateway_name = str(pending_action.get("gateway_name") or pending_action.get("tool_name") or "").strip()
        args = pending_action.get("args") if isinstance(pending_action.get("args"), dict) else {}
        if not self.approval_repo or not action_id:
            raise RuntimeError("Pending action repository or action id is missing.")
        claimed = self.approval_repo.claim_pending_action(
            action_id=action_id,
            chat_id=context.chat_id,
            user_id=context.user_id,
        )
        if not claimed:
            raise RuntimeError("Pending action is no longer available for this user.")
        pending_action = claimed
        gateway_name = str(pending_action.get("gateway_name") or pending_action.get("tool_name") or "").strip()
        args = pending_action.get("args") if isinstance(pending_action.get("args"), dict) else {}
        try:
            if gateway_name.startswith("code."):
                endpoint = str(args.get("endpoint") or "").strip()
                payload = args.get("payload") if isinstance(args.get("payload"), dict) else {}
                if self.code_runner_client is None:
                    raise RuntimeError("Code runner client is not configured.")
                data = self.code_runner_client.request(endpoint, payload)
                ok = bool(data.get("ok", True))
                text = str(data.get("text") or "").strip()
                result = ToolGatewayResult(ok=ok, tool=gateway_name, text=text, payload=data)
            else:
                result = self.run_tool(
                    gateway_name,
                    dict(args),
                    context,
                    request_text=request_text,
                    force_execute=True,
                )
        except Exception as exc:
            if self.approval_repo and action_id:
                try:
                    self.approval_repo.mark_pending_action_status(
                        action_id,
                        "failed",
                        error_text=str(exc),
                    )
                except Exception:
                    pass
            raise

        if self.approval_repo and action_id:
            try:
                self.approval_repo.mark_pending_action_status(
                    action_id,
                    "executed" if result.ok else "failed",
                    result_text=result.text,
                )
            except Exception:
                pass
        return result
