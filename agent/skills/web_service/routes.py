from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agent.error_envelope import ErrorSource, build_exception_envelope
from agent.i18n import t

from .schemas import WebRequest, WebResult
from .service import WebService


router = APIRouter(prefix="/mia/web", tags=["mia-web"])


def _get_service(request: Request) -> WebService:
    service = getattr(request.app.state, "web_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Web service is not ready.")
    return service


def _error_result(*, tool: str, exc: Exception, request_id: str = "", chat_id: str = "", url: str = "") -> WebResult:
    category = "validation" if isinstance(exc, ValueError) else "internal"
    envelope = build_exception_envelope(
        exc,
        code=f"{tool}_failed",
        category=category,
        severity="warn" if category == "validation" else "error",
        user_message=str(exc) if category == "validation" else t("error.url_unprocessed", default="Mia chưa xử lý được link này. Bạn thử lại nhé."),
        retryable=False,
        source=ErrorSource(
            layer="api",
            component="web",
            operation=tool,
        ),
        request_id=request_id,
        chat_id=chat_id,
        details={"url": url},
    )
    return WebResult(
        ok=False,
        tool=tool,
        url=url,
        text=envelope.display_text(),
        data={
            "request_id": request_id,
            "chat_id": chat_id,
            "url": url,
            "error": envelope.model_dump(mode="json"),
        },
        warnings=[],
        trace={},
        error=envelope,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mia-web"}


@router.post("/read-url", response_model=WebResult)
def read_url(request: Request, payload: WebRequest) -> WebResult:
    service = _get_service(request)
    try:
        return service.read_url(
            url=payload.url,
            instruction=payload.prompt or payload.instruction or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
            fetch_strategy=payload.fetch_strategy,
            max_chars=payload.max_chars,
        )
    except Exception as exc:
        return _error_result(tool="read_url", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, url=payload.url)


@router.post("/summarize-url", response_model=WebResult)
def summarize_url(request: Request, payload: WebRequest) -> WebResult:
    service = _get_service(request)
    try:
        return service.summarize_url(
            url=payload.url,
            instruction=payload.prompt or payload.instruction or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
            fetch_strategy=payload.fetch_strategy,
            max_chars=payload.max_chars,
        )
    except Exception as exc:
        return _error_result(tool="summarize_url", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, url=payload.url)


@router.post("/ask-url", response_model=WebResult)
def ask_url(request: Request, payload: WebRequest) -> WebResult:
    service = _get_service(request)
    try:
        return service.ask_url(
            url=payload.url,
            instruction=payload.question or payload.prompt or payload.instruction or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
            fetch_strategy=payload.fetch_strategy,
            max_chars=payload.max_chars,
        )
    except Exception as exc:
        return _error_result(tool="ask_url", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, url=payload.url)
