from __future__ import annotations

import re
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field


ErrorCategory = Literal[
    "validation",
    "not_found",
    "unauthorized",
    "forbidden",
    "timeout",
    "rate_limit",
    "unavailable",
    "approval_required",
    "external",
    "internal",
    "cancelled",
    "conflict",
]

ErrorSeverity = Literal["info", "warn", "error", "critical"]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _clean_display_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _truncate_text(value: Any, limit: int = 1200) -> str:
    text = _clean_text(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _slugify(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "").strip().lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return clean or "error"


def _normalize_actions(values: Iterable[str] | None) -> list[str]:
    actions: list[str] = []
    for value in values or []:
        clean = _clean_display_text(value)
        if clean and clean not in actions:
            actions.append(clean)
    return actions


class ErrorSource(BaseModel):
    model_config = ConfigDict(extra="ignore")

    layer: str = "unknown"
    component: str = ""
    operation: str = ""
    tool: str = ""
    workflow: str = ""
    node: str = ""
    provider: str = ""


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    code: str = "internal_error"
    category: ErrorCategory = "internal"
    severity: ErrorSeverity = "error"
    message: str = ""
    user_message: str = ""
    retryable: bool = False
    source: ErrorSource = Field(default_factory=ErrorSource)
    details: dict[str, Any] = Field(default_factory=dict)
    suggested_actions: list[str] = Field(default_factory=list)
    request_id: str = ""
    thread_id: str = ""
    chat_id: str = ""
    status_code: int | None = None
    retry_after_seconds: int | None = None
    exception_type: str = ""
    trace: dict[str, Any] = Field(default_factory=dict)

    def display_text(self) -> str:
        return _clean_display_text(
            self.user_message
            or self.message
            or "Mia gặp lỗi không mong đợi. Bạn thử lại giúp mình nhé."
        )

    @classmethod
    def build(
        cls,
        *,
        code: str = "internal_error",
        category: ErrorCategory = "internal",
        severity: ErrorSeverity = "error",
        message: str = "",
        user_message: str = "",
        retryable: bool = False,
        source: ErrorSource | None = None,
        details: dict[str, Any] | None = None,
        suggested_actions: Iterable[str] | None = None,
        request_id: str = "",
        thread_id: str = "",
        chat_id: str = "",
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
        exception_type: str = "",
        trace: dict[str, Any] | None = None,
    ) -> "ErrorEnvelope":
        return cls(
            ok=False,
            code=_clean_text(code) or "internal_error",
            category=category,
            severity=severity,
            message=_clean_text(message),
            user_message=_clean_display_text(user_message),
            retryable=bool(retryable),
            source=source or ErrorSource(),
            details=dict(details or {}),
            suggested_actions=_normalize_actions(suggested_actions),
            request_id=_clean_text(request_id),
            thread_id=_clean_text(thread_id),
            chat_id=_clean_text(chat_id),
            status_code=int(status_code) if status_code is not None else None,
            retry_after_seconds=int(retry_after_seconds) if retry_after_seconds is not None else None,
            exception_type=_clean_text(exception_type),
            trace=dict(trace or {}),
        )


def _http_status_classification(status_code: int) -> tuple[str, ErrorCategory, ErrorSeverity, bool, str, list[str]]:
    if status_code == 404:
        return (
            "tool_not_found",
            "not_found",
            "warn",
            False,
            "Mình không tìm thấy tài nguyên mà tool cần để tiếp tục.",
            [
                "Kiểm tra lại tên file, URL hoặc repo.",
                "Nếu là GitHub, hãy xác nhận repo và đường dẫn có tồn tại.",
            ],
        )
    if status_code in {400, 422}:
        return (
            "tool_invalid_input",
            "validation",
            "warn",
            False,
            "Dữ liệu đầu vào của tool chưa hợp lệ.",
            [
                "Kiểm tra lại tham số gửi vào tool.",
                "Nếu là URL hoặc path, hãy xác nhận định dạng chính xác.",
            ],
        )
    if status_code == 401:
        return (
            "tool_unauthorized",
            "unauthorized",
            "error",
            False,
            "Cần xác thực để truy cập tài nguyên này.",
            [
                "Kiểm tra credential hoặc token.",
                "Xác nhận tài khoản có quyền truy cập tài nguyên.",
            ],
        )
    if status_code == 403:
        return (
            "tool_forbidden",
            "forbidden",
            "error",
            False,
            "Tài nguyên này đang bị giới hạn quyền truy cập.",
            [
                "Kiểm tra quyền truy cập của credential.",
                "Nếu đây là repo hoặc file private, hãy xác nhận quyền đọc.",
            ],
        )
    if status_code == 408:
        return (
            "tool_timeout",
            "timeout",
            "warn",
            True,
            "Tool gateway phản hồi quá chậm, bạn thử lại sau nhé.",
            [
                "Thử lại sau vài giây.",
                "Nếu lỗi lặp lại, kiểm tra timeout hoặc tải hệ thống.",
            ],
        )
    if status_code == 429:
        return (
            "tool_rate_limited",
            "rate_limit",
            "warn",
            True,
            "Bên ngoài đang giới hạn tần suất, bạn thử lại sau nhé.",
            [
                "Chờ một lát rồi thử lại.",
                "Giảm tần suất gọi tool nếu có thể.",
            ],
        )
    if status_code in {500, 502, 503, 504}:
        return (
            "tool_unavailable",
            "unavailable",
            "error",
            True,
            "Dịch vụ bên ngoài đang gặp sự cố hoặc chưa phản hồi ổn định.",
            [
                "Thử lại sau ít phút.",
                "Nếu lỗi kéo dài, kiểm tra service bên ngoài hoặc workflow upstream.",
            ],
        )
    if status_code == 409:
        return (
            "tool_conflict",
            "conflict",
            "warn",
            False,
            "Yêu cầu này đang xung đột với trạng thái hiện tại.",
            [
                "Kiểm tra xem tài nguyên đã thay đổi chưa.",
                "Thử lại với dữ liệu mới nhất.",
            ],
        )
    return (
        f"tool_http_{status_code}",
        "external",
        "error",
        status_code >= 500,
        f"Tool gateway trả về HTTP {status_code}.",
        [
            "Kiểm tra response của workflow con.",
            "Nếu là lỗi tạm thời, thử lại sau.",
        ],
    )


def build_tool_http_error_envelope(
    *,
    tool_name: str,
    status_code: int,
    response_text: str = "",
    error_text: str = "",
    request_id: str = "",
    thread_id: str = "",
    chat_id: str = "",
    source: ErrorSource | None = None,
    retry_after_seconds: int | None = None,
) -> ErrorEnvelope:
    code, category, severity, retryable, user_message, suggested_actions = _http_status_classification(status_code)
    details = {
        "tool_name": _clean_text(tool_name),
        "status_code": int(status_code),
        "response_excerpt": _truncate_text(response_text, 1200),
    }
    if error_text:
        details["error_text"] = _truncate_text(error_text, 500)
    return ErrorEnvelope.build(
        code=code,
        category=category,
        severity=severity,
        message=_clean_text(error_text or f"{tool_name} failed: HTTP {status_code}"),
        user_message=user_message,
        retryable=retryable,
        source=source
        or ErrorSource(
            layer="tool_gateway",
            component="n8n_client",
            operation="run_tool",
            tool=_clean_text(tool_name),
            workflow="Mia: Tool Gateway",
        ),
        details=details,
        suggested_actions=suggested_actions,
        request_id=request_id,
        thread_id=thread_id,
        chat_id=chat_id,
        status_code=status_code,
        retry_after_seconds=retry_after_seconds,
        exception_type="HTTPStatusError",
        trace={"response_text": _truncate_text(response_text, 1200)},
    )


def build_tool_transport_error_envelope(
    *,
    tool_name: str,
    error_text: str,
    timeout: bool = False,
    request_id: str = "",
    thread_id: str = "",
    chat_id: str = "",
    source: ErrorSource | None = None,
) -> ErrorEnvelope:
    category: ErrorCategory = "timeout" if timeout else "unavailable"
    severity: ErrorSeverity = "warn" if timeout else "error"
    code = "tool_timeout" if timeout else "tool_transport_error"
    user_message = (
        "Tool gateway phản hồi quá chậm, bạn thử lại sau nhé."
        if timeout
        else "Mình không kết nối được tới tool gateway."
    )
    suggested_actions = (
        [
            "Thử lại sau vài giây.",
            "Nếu lỗi lặp lại, kiểm tra timeout hoặc tải hệ thống.",
        ]
        if timeout
        else [
            "Kiểm tra mạng hoặc endpoint của tool gateway.",
            "Thử lại sau nếu đây là lỗi tạm thời.",
        ]
    )
    return ErrorEnvelope.build(
        code=code,
        category=category,
        severity=severity,
        message=_clean_text(error_text or user_message),
        user_message=user_message,
        retryable=True,
        source=source
        or ErrorSource(
            layer="tool_gateway",
            component="n8n_client",
            operation="run_tool",
            tool=_clean_text(tool_name),
            workflow="Mia: Tool Gateway",
        ),
        details={
            "tool_name": _clean_text(tool_name),
            "error_text": _truncate_text(error_text, 500),
        },
        suggested_actions=suggested_actions,
        request_id=request_id,
        thread_id=thread_id,
        chat_id=chat_id,
        exception_type="TimeoutException" if timeout else "RequestError",
        trace={"error_text": _truncate_text(error_text, 500)},
    )


def build_tool_result_error_envelope(
    *,
    tool_name: str,
    error_text: str,
    response_text: str = "",
    status_text: str = "",
    status_code: int | None = None,
    retryable: bool = False,
    request_id: str = "",
    thread_id: str = "",
    chat_id: str = "",
    source: ErrorSource | None = None,
) -> ErrorEnvelope:
    category: ErrorCategory = "external"
    severity: ErrorSeverity = "warn" if retryable else "error"
    code = _slugify(status_text) if status_text else "tool_failed"
    user_message = _clean_display_text(response_text or error_text or "Mia gặp lỗi từ tool gateway.")
    suggested_actions = (
        [
            "Thử lại sau nếu đây là lỗi tạm thời.",
            "Nếu lỗi lặp lại, kiểm tra input hoặc workflow con.",
        ]
        if retryable
        else [
            "Kiểm tra lại input hoặc cấu hình workflow con.",
            "Nếu là lỗi dữ liệu, thử lại với đầu vào rõ ràng hơn.",
        ]
    )
    return ErrorEnvelope.build(
        code=code,
        category=category,
        severity=severity,
        message=_clean_text(error_text or user_message),
        user_message=user_message,
        retryable=retryable,
        source=source
        or ErrorSource(
            layer="tool_gateway",
            component="n8n_client",
            operation="run_tool",
            tool=_clean_text(tool_name),
            workflow="Mia: Tool Gateway",
        ),
        details={
            "tool_name": _clean_text(tool_name),
            "status_text": _clean_text(status_text),
            "response_excerpt": _truncate_text(response_text, 1200),
            "error_text": _truncate_text(error_text, 500),
        },
        suggested_actions=suggested_actions,
        request_id=request_id,
        thread_id=thread_id,
        chat_id=chat_id,
        status_code=status_code,
        exception_type="ToolResultError",
        trace={
            "status_text": _clean_text(status_text),
            "response_text": _truncate_text(response_text, 1200),
        },
    )


def build_approval_required_envelope(
    *,
    tool_name: str,
    summary: str,
    pending_action_id: int | None = None,
    request_id: str = "",
    thread_id: str = "",
    chat_id: str = "",
    source: ErrorSource | None = None,
) -> ErrorEnvelope:
    display_text = (
        "Thao tác này cần xác nhận trước khi thực hiện.\n"
        f"- {_clean_display_text(summary) or _clean_display_text(tool_name)}\n"
        "Nếu anh Minh muốn tiếp tục, hãy nhắn: xác nhận"
    )
    return ErrorEnvelope.build(
        code="approval_required",
        category="approval_required",
        severity="warn",
        message=f"{_clean_text(tool_name)} requires explicit confirmation.",
        user_message=display_text,
        retryable=False,
        source=source
        or ErrorSource(
            layer="tool_gateway",
            component="approval",
            operation="create_pending_action",
            tool=_clean_text(tool_name),
            workflow="Mia: Tool Gateway",
        ),
        details={
            "tool_name": _clean_text(tool_name),
            "summary": _clean_display_text(summary),
            "pending_action_id": int(pending_action_id) if pending_action_id is not None else None,
        },
        suggested_actions=["Nhắn 'xác nhận' để tiếp tục."],
        request_id=request_id,
        thread_id=thread_id,
        chat_id=chat_id,
        exception_type="ApprovalRequired",
    )


def build_exception_envelope(
    exc: Exception,
    *,
    code: str = "",
    category: ErrorCategory = "internal",
    severity: ErrorSeverity = "error",
    user_message: str = "",
    retryable: bool = False,
    source: ErrorSource | None = None,
    details: dict[str, Any] | None = None,
    suggested_actions: Iterable[str] | None = None,
    request_id: str = "",
    thread_id: str = "",
    chat_id: str = "",
    status_code: int | None = None,
    retry_after_seconds: int | None = None,
    trace: dict[str, Any] | None = None,
) -> ErrorEnvelope:
    return ErrorEnvelope.build(
        code=code or _slugify(exc.__class__.__name__),
        category=category,
        severity=severity,
        message=_clean_text(str(exc) or exc.__class__.__name__),
        user_message=user_message or "Mia gặp lỗi không mong đợi. Bạn thử lại giúp mình nhé.",
        retryable=retryable,
        source=source or ErrorSource(),
        details=dict(details or {}),
        suggested_actions=suggested_actions,
        request_id=request_id,
        thread_id=thread_id,
        chat_id=chat_id,
        status_code=status_code,
        retry_after_seconds=retry_after_seconds,
        exception_type=exc.__class__.__name__,
        trace=trace,
    )
