from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from mia_core.error_envelope import ErrorSource, build_exception_envelope
from mia_core.media.schemas import MediaRequest, MediaResult
from mia_core.media.service import MediaService


router = APIRouter(prefix="/mia/media", tags=["mia-media"])


def _get_service(request: Request) -> MediaService:
    service = getattr(request.app.state, "media_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Media service is not ready.")
    return service


def _result_to_response(result: MediaResult) -> MediaResult:
    return result


def _error_result(*, tool: str, exc: Exception, request_id: str = "", chat_id: str = "", file_name: str = "") -> MediaResult:
    category = "validation" if isinstance(exc, ValueError) else "internal"
    envelope = build_exception_envelope(
        exc,
        code=f"{tool}_failed",
        category=category,
        severity="warn" if category == "validation" else "error",
        user_message=str(exc) if category == "validation" else "Mia chưa xử lý được tệp này. Bạn thử lại nhé.",
        retryable=False,
        source=ErrorSource(
            layer="api",
            component="media",
            operation=tool,
        ),
        request_id=request_id,
        chat_id=chat_id,
        details={"file_name": file_name},
    )
    return MediaResult(
        ok=False,
        tool=tool,
        text=envelope.display_text(),
        data={
            "request_id": request_id,
            "chat_id": chat_id,
            "file_name": file_name,
            "error": envelope.model_dump(mode="json"),
        },
        file_name=file_name,
        warnings=[],
        trace={},
        error=envelope,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mia-media"}


@router.post("/image/ocr", response_model=MediaResult)
def image_ocr(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return _result_to_response(
            service.image_ocr(
                file_base64=payload.file_base64,
                file_name=payload.file_name,
                mime_type=payload.mime_type,
                attachment_kind=payload.attachment_kind or "photo",
                instruction=payload.prompt or payload.text,
                request_id=payload.request_id,
                chat_id=payload.chat_id,
            )
        )
    except Exception as exc:
        return _error_result(tool="image_ocr", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/image/describe", response_model=MediaResult)
def image_describe(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.image_describe(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "photo",
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="image_describe", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/image/extract-fields", response_model=MediaResult)
def image_extract_fields(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.image_extract_fields(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "photo",
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="image_extract_fields", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/document/extract-text", response_model=MediaResult)
def document_extract_text(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.document_extract_text(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "document",
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="document_extract_text", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/document/summarize", response_model=MediaResult)
def document_summarize(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.document_summarize(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "document",
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="document_summarize", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/document/search-answer", response_model=MediaResult)
def document_search_answer(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.document_search_answer(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "document",
            question=payload.question or payload.text,
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="document_search_answer", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/document/extract-fields", response_model=MediaResult)
def document_extract_fields(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.document_extract_fields(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "document",
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="document_extract_fields", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/audio/transcribe", response_model=MediaResult)
def audio_transcribe(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.audio_transcribe(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "audio",
            language=payload.language,
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="audio_transcribe", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/audio/summarize", response_model=MediaResult)
def audio_summarize(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.audio_summarize(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "audio",
            language=payload.language,
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="audio_summarize", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/video/transcribe", response_model=MediaResult)
def video_transcribe(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.video_transcribe(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "video",
            language=payload.language,
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="video_transcribe", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/video/summarize", response_model=MediaResult)
def video_summarize(request: Request, payload: MediaRequest) -> MediaResult:
    service = _get_service(request)
    try:
        return service.video_summarize(
            file_base64=payload.file_base64,
            file_name=payload.file_name,
            mime_type=payload.mime_type,
            attachment_kind=payload.attachment_kind or "video",
            language=payload.language,
            instruction=payload.prompt or payload.text,
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
    except Exception as exc:
        return _error_result(tool="video_summarize", exc=exc, request_id=payload.request_id, chat_id=payload.chat_id, file_name=payload.file_name)


@router.post("/tts/speak")
def tts_speak(request: Request, payload: MediaRequest) -> Response:
    service = _get_service(request)
    try:
        audio_bytes, content_type, filename = service.tts_speak(
            text=payload.text or payload.prompt,
            model=payload.model,
            voice=payload.voice,
            response_format="",
            request_id=payload.request_id,
            chat_id=payload.chat_id,
        )
        if (payload.response_mode or "audio").lower() == "json":
            import base64

            return JSONResponse(
                {
                    "tool": "tts_speak",
                    "text": payload.text or payload.prompt,
                    "mime_type": content_type or "audio/mpeg",
                    "file_name": filename,
                    "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
                }
            )
        return Response(
            content=audio_bytes,
            media_type=content_type or "audio/mpeg",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"',
            },
        )
    except Exception as exc:
        envelope = build_exception_envelope(
            exc,
            code="tts_speak_failed",
            category="validation" if isinstance(exc, ValueError) else "internal",
            severity="warn" if isinstance(exc, ValueError) else "error",
            user_message=str(exc) if isinstance(exc, ValueError) else "Mia chưa tạo được audio này. Bạn thử lại nhé.",
            retryable=False,
            source=ErrorSource(
                layer="api",
                component="media",
                operation="tts_speak",
            ),
            request_id=payload.request_id,
            chat_id=payload.chat_id,
            details={"file_name": payload.file_name},
        )
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "tool": "tts_speak",
                "text": envelope.display_text(),
                "data": {
                    "request_id": payload.request_id,
                    "chat_id": payload.chat_id,
                    "file_name": payload.file_name,
                },
                "error": envelope.model_dump(mode="json"),
            },
        )
