from __future__ import annotations

from typing import Any
from langchain.messages import HumanMessage, SystemMessage
from agent.error_envelope import ErrorEnvelope
from agent.models import MiaChatRequest, MiaChatResponse, MiaContext
from agent.persona.followup_cues import DOCUMENT_FOLLOWUP_CUES, URL_FOLLOWUP_CUES
from agent.i18n import t
from agent.brain.response_normalizer import (
    coerce_message_text as normalized_coerce_message_text,
    sanitize_final_text as normalized_sanitize_final_text,
)


class FollowupHandler:
    def __init__(self, service: Any) -> None:
        self.service = service
        self.memory_repo = service.memory_repo
        self.document_followup_model = service.document_followup_model
        self.document_followup_fallback_model = service.document_followup_fallback_model

    @staticmethod
    def _error_response(request: MiaChatRequest, error: ErrorEnvelope, *, tool_name: str) -> MiaChatResponse:
        return MiaChatResponse(
            ok=False,
            final_text=error.display_text(),
            tools_called=[tool_name] if tool_name else [],
            thread_id=request.resolved_thread_id(),
            request_id=request.resolved_request_id(),
            trace={"error": error.model_dump(mode="json")},
            error=error,
        )

    def _try_document_memory_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        text = " ".join(str(request.text or "").split()).strip()
        if not text:
            return None

        normalized = text.lower()
        has_question_mark = "?" in text
        looks_like_followup = has_question_mark or any(cue in normalized for cue in DOCUMENT_FOLLOWUP_CUES)
        if not looks_like_followup:
            return None

        rows = self.memory_repo.search(
            chat_id=request.chat_id,
            query=request.text,
            limit=3,
            memory_type="document_context",
        )
        if not rows:
            return None

        context_lines: list[str] = []
        title = ""
        for index, row in enumerate(rows, start=1):
            row_title = str(row.get("title") or "").strip()
            chunk_text = str(row.get("chunk_text") or "").strip()
            if row_title and not title:
                title = row_title
            if chunk_text:
                context_lines.append(t("skills.match_part", default="Phần khớp {index}: {chunk_text}", index=index, chunk_text=chunk_text))

        if not context_lines:
            return None

        learning_guidance = self.service._learning_guidance_text(
            scopes=["general", "document", "document_followup"],
            limit=3,
        )
        try:
            result, provider_used = self.service._invoke_model_with_fallback(
                self.document_followup_model,
                self.document_followup_fallback_model,
                [
                    SystemMessage(
                        content=t("skills.doc_followup_system")
                    ),
                    *([SystemMessage(content=learning_guidance)] if learning_guidance else []),
                    HumanMessage(
                        content=t(
                            "skills.doc_followup_human",
                            title=title or t("skills.unknown", default="không rõ"),
                            text=text,
                            context="\n\n".join(context_lines)
                        )
                    ),
                ],
                scope="agent:document-followup",
            )
        except Exception as exc:
            error = ErrorEnvelope.build(
                code="document_followup_failed",
                category="unavailable",
                severity="error",
                message=str(exc),
                user_message=t("error.document_followup_failed"),
                retryable=True,
                request_id=request.resolved_request_id(),
                thread_id=request.resolved_thread_id(),
                chat_id=request.chat_id,
                details={"tool_name": "memory_search"},
                exception_type=exc.__class__.__name__,
            )
            return self._error_response(request, error, tool_name="memory_search")
        final_text = normalized_sanitize_final_text(normalized_coerce_message_text(result.content))
        if not final_text:
            return None

        trace = self.service._cache_trace(result, scope="agent:document-followup", provider_used=provider_used)
        trace["provider"] = provider_used
        self.service._record_learning_event(
            request=request,
            source="followup",
            scope="document",
            topic="document_followup",
            final_text=final_text,
            tools_called=["memory_search"],
            trace={"llm": trace},
            notes="document memory follow-up",
        )

        return MiaChatResponse(
            final_text=final_text,
            tools_called=["memory_search"],
            thread_id=request.resolved_thread_id(),
            request_id=request.resolved_request_id(),
            trace={"llm": trace},
        )

    def _try_url_memory_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        text = " ".join(str(request.text or "").split()).strip()
        if not text:
            return None

        normalized = text.lower()
        has_question_mark = "?" in text
        looks_like_followup = has_question_mark or any(cue in normalized for cue in URL_FOLLOWUP_CUES)
        if not looks_like_followup:
            return None

        rows = self.memory_repo.search(
            chat_id=request.chat_id,
            query=request.text,
            limit=3,
            memory_type="url_context",
        )
        if not rows:
            return None

        context_lines: list[str] = []
        title = ""
        for index, row in enumerate(rows, start=1):
            row_title = str(row.get("title") or "").strip()
            chunk_text = str(row.get("chunk_text") or "").strip()
            if row_title and not title:
                title = row_title
            if chunk_text:
                context_lines.append(t("skills.match_part", default="Phần khớp {index}: {chunk_text}", index=index, chunk_text=chunk_text))

        if not context_lines:
            return None

        learning_guidance = self.service._learning_guidance_text(
            scopes=["general", "web"],
            limit=3,
        )
        try:
            result, provider_used = self.service._invoke_model_with_fallback(
                self.document_followup_model,
                self.document_followup_fallback_model,
                [
                    SystemMessage(
                        content=t("skills.url_followup_system")
                    ),
                    *([SystemMessage(content=learning_guidance)] if learning_guidance else []),
                    HumanMessage(
                        content=t(
                            "skills.url_followup_human",
                            title=title or t("skills.unknown", default="không rõ"),
                            text=text,
                            context="\n\n".join(context_lines)
                        )
                    ),
                ],
                scope="agent:url-followup",
            )
        except Exception as exc:
            error = ErrorEnvelope.build(
                code="url_followup_failed",
                category="unavailable",
                severity="error",
                message=str(exc),
                user_message=t("error.url_followup_failed"),
                retryable=True,
                request_id=request.resolved_request_id(),
                thread_id=request.resolved_thread_id(),
                chat_id=request.chat_id,
                details={"tool_name": "memory_search"},
                exception_type=exc.__class__.__name__,
            )
            return self._error_response(request, error, tool_name="memory_search")
        final_text = normalized_sanitize_final_text(normalized_coerce_message_text(result.content))
        if not final_text:
            return None

        trace = self.service._cache_trace(result, scope="agent:url-followup", provider_used=provider_used)
        trace["provider"] = provider_used
        self.service._record_learning_event(
            request=request,
            source="followup",
            scope="web",
            topic="ask_url",
            final_text=final_text,
            tools_called=["memory_search"],
            trace={"llm": trace},
            notes="url memory follow-up",
        )

        return MiaChatResponse(
            final_text=final_text,
            tools_called=["memory_search"],
            thread_id=request.resolved_thread_id(),
            request_id=request.resolved_request_id(),
            trace={"llm": trace},
        )
