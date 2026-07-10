from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain.messages import HumanMessage, SystemMessage

from agent.config import Settings
from agent.i18n import t
from agent.learning.repository import LearningRepository, build_learning_guidance_text, classify_learning_issue
from agent.skills.media_service.groq_client import GroqMediaClient, GroqTranscriptionResult
from agent.skills.media_service.local import (
    compact_text,
    extract_document_text,
    extract_text_from_image_bytes,
    image_basic_stats,
    image_to_data_url,
    is_image,
    parse_structured_fields,
    normalize_spaces,
)
from agent.skills.media_service.schemas import MediaResult
from agent.brain.llm_provider import build_primary_and_fallback_models
from agent.brain.prompt_cache import build_prompt_cache_key
from agent.brain.trace_utils import extract_prompt_cache_trace


@dataclass(frozen=True)
class MediaBytes:
    file_name: str
    mime_type: str
    attachment_kind: str
    data: bytes


class MediaService:
    def __init__(self, settings: Settings, learning_repo: LearningRepository | None = None) -> None:
        self.settings = settings
        self.learning_repo = learning_repo
        self.analysis_models: dict[str, Any] = {}
        self.analysis_fallback_models: dict[str, Any | None] = {}
        self.analysis_model, self.analysis_model_fallback = self._get_analysis_model("media:summary:default")
        self.groq = GroqMediaClient(api_key=self.settings.groq_api_key, base_url=self.settings.groq_base_url)

    @staticmethod
    def _learning_scopes(*, tool: str, attachment_kind: str) -> list[str]:
        scopes = ["media", "general"]
        tool_name = str(tool or "").strip()
        kind = str(attachment_kind or "").strip()
        for value in (tool_name, kind):
            if value and value not in scopes:
                scopes.append(value)
        if tool_name.startswith("document_"):
            for extra in ("document", "media:document"):
                if extra not in scopes:
                    scopes.append(extra)
        if tool_name.startswith("image_"):
            for extra in ("image", "media:image"):
                if extra not in scopes:
                    scopes.append(extra)
        if tool_name.startswith("audio_"):
            for extra in ("audio", "media:audio"):
                if extra not in scopes:
                    scopes.append(extra)
        if tool_name.startswith("video_"):
            for extra in ("video", "media:video"):
                if extra not in scopes:
                    scopes.append(extra)
        return scopes

    def _learning_guidance_text(self, *, tool: str, attachment_kind: str, limit: int = 4) -> str:
        if not self.learning_repo:
            return ""
        rows = self.learning_repo.list_active_insights(
            scopes=self._learning_scopes(tool=tool, attachment_kind=attachment_kind),
            limit=limit,
        )
        return build_learning_guidance_text(rows, limit=limit)

    def _record_learning_event(
        self,
        *,
        tool: str,
        request_text: str,
        final_text: str,
        attachment_kind: str,
        trace: dict[str, Any] | None,
        warnings: list[str] | None = None,
        file_name: str = "",
        mime_type: str = "",
        request_id: str = "",
        chat_id: str = "",
        notes: str = "",
    ) -> None:
        if not self.learning_repo:
            return
        issue_type, severity, issue_note = classify_learning_issue(
            request_text=request_text,
            final_text=final_text,
            tools_called=[tool] if tool else [],
            trace=trace or {},
            source="media",
            scope="document" if tool.startswith("document_") else "image" if tool.startswith("image_") else "audio" if tool.startswith("audio_") else "video" if tool.startswith("video_") else "media",
            topic=tool,
            warnings=warnings or [],
        )
        merged_notes = "\n".join(part for part in [notes.strip(), issue_note.strip()] if part).strip()
        try:
            self.learning_repo.record_event(
                chat_id=chat_id or file_name or "media",
                request_id=request_id or file_name or "media",
                thread_id="",
                source="media",
                scope="document" if tool.startswith("document_") else "image" if tool.startswith("image_") else "audio" if tool.startswith("audio_") else "video" if tool.startswith("video_") else "media",
                topic=tool,
                user_text=request_text,
                final_text=final_text,
                tools_called=[tool] if tool else [],
                trace=trace or {},
                issue_type=issue_type,
                severity=severity,
                notes=merged_notes,
                metadata={
                    "file_name": file_name,
                    "mime_type": mime_type,
                    "attachment_kind": attachment_kind,
                },
            )
        except Exception:
            pass

    def _get_analysis_model(self, scope: str) -> tuple[Any, Any | None]:
        if scope not in self.analysis_models:
            primary, fallback = build_primary_and_fallback_models(
                self.settings,
                scope=scope,
                temperature=0,
                max_tokens=900,
            )
            self.analysis_models[scope] = primary
            self.analysis_fallback_models[scope] = fallback
        return self.analysis_models[scope], self.analysis_fallback_models.get(scope)

    def _analysis_model_name(self, provider_used: str) -> str:
        if self.settings.primary_llm_provider == "deepseek_direct" and provider_used == "primary":
            return self.settings.deepseek_model
        return self.settings.model

    def _analysis_cache_key(self, scope: str, *, provider_used: str = "primary") -> str:
        if not self.settings.prompt_cache_enabled:
            return ""
        provider_name = self.settings.primary_llm_provider if provider_used != "fallback" else "openrouter"
        return build_prompt_cache_key(
            namespace=self.settings.prompt_cache_namespace,
            scope=f"{provider_name}:{scope}",
            version=self.settings.prompt_cache_version,
        )

    def _invoke_analysis(self, messages: list[Any], *, scope: str) -> tuple[Any, str]:
        primary, fallback = self._get_analysis_model(scope)
        try:
            return primary.invoke(messages), "primary"
        except Exception as primary_exc:
            if fallback is None:
                raise
            try:
                return fallback.invoke(messages), "fallback"
            except Exception:
                raise primary_exc

    def _analysis_trace(self, result: Any, *, scope: str, provider_used: str = "primary") -> dict[str, Any]:
        return extract_prompt_cache_trace(
            result,
            scope=scope,
            model=self._analysis_model_name(provider_used),
            prompt_cache_key=self._analysis_cache_key(scope, provider_used=provider_used),
        )

    def _summarize_text(
        self,
        text: str,
        *,
        instruction: str = "",
        title: str = "",
        learning_hint: str = "",
        style: str = "default",
        content_limit: int = 18000,
        deep: bool = False,
        cache_scope: str | None = None,
        capture_trace: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        content = compact_text(text, limit=content_limit)
        if not content:
            return ""
        if style == "document":
            doc_placeholder = t("skills.document_placeholder")
            resolved_title = title or doc_placeholder
            if deep:
                prompt = instruction.strip() or t("skills.media_doc_summary_deep_prompt", title=resolved_title)
            else:
                prompt = instruction.strip() or t("skills.media_doc_summary_normal_prompt", title=resolved_title)
            system_prompt = t("skills.media_doc_llm_system")
            if deep:
                closing_prompt = t("skills.media_doc_summary_deep_closing", title=resolved_title)
            else:
                closing_prompt = t("skills.media_doc_summary_normal_closing", title=resolved_title)
        else:
            doc_placeholder = t("skills.document_placeholder")
            resolved_title = title or doc_placeholder
            prompt = instruction.strip() or t("skills.media_summary_default_prompt", title=resolved_title)
            system_prompt = t("skills.media_summary_default_system")
            closing_prompt = t("skills.media_summary_default_closing")
        if learning_hint.strip():
            prompt = f"{prompt}\n\n" + t("skills.media_notes_header", hint=learning_hint.strip())
        scope = cache_scope or (
            "media:document-summary:deep" if style == "document" and deep else
            "media:document-summary:normal" if style == "document" else
            "media:summary:default"
        )
        result, provider_used = self._invoke_analysis(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(
                    content=(
                        f"{prompt}\n\n"
                        f"Nội dung:\n{content}\n\n"
                        f"{closing_prompt}"
                    )
                ),
            ],
            scope=scope,
        )
        summary_text = str(result.content).strip()
        if capture_trace:
            return summary_text, self._analysis_trace(result, scope=scope, provider_used=provider_used)
        return summary_text

    @staticmethod
    def _is_deep_document_summary_request(*, instruction: str, text: str, page_count: int = 0) -> bool:
        normalized_instruction = normalize_spaces((instruction or "").lower())
        normalized_text = normalize_spaces((text or "").lower())
        cues = (
            "phân tích sâu",
            "phân tích kỹ",
            "tóm tắt kỹ",
            "tóm tắt chi tiết",
            "chi tiết hơn",
            "kỹ hơn",
            "đầy đủ hơn",
            "nhiều trang",
            "nhiều page",
            "đọc kỹ",
            "bóc tách",
            "deep",
            "analysis",
        )
        if any(cue in normalized_instruction for cue in cues):
            return True
        if "phân tích" in normalized_instruction and any(cue in normalized_instruction for cue in ("kỹ", "sâu", "chi tiết", "đầy đủ")):
            return True
        if page_count >= 6:
            return True
        if len(normalized_text) >= 12000:
            return True
        return False

    @staticmethod
    def _chunk_text_for_summary(text: str, *, target_chunk_size: int = 4500, max_chunks: int = 6) -> list[str]:
        cleaned = normalize_spaces(text)
        if not cleaned:
            return []
        paragraphs = [normalize_spaces(part) for part in re.split(r"\n{2,}", text) if normalize_spaces(part)]
        if not paragraphs:
            paragraphs = [cleaned]
        chunks: list[str] = []
        current = ""
        for paragraph in paragraphs:
            candidate = paragraph if not current else f"{current}\n\n{paragraph}"
            if len(candidate) <= target_chunk_size or not current:
                current = candidate
                continue
            chunks.append(current.strip())
            current = paragraph
            if len(chunks) >= max_chunks:
                break
        if current and len(chunks) < max_chunks:
            chunks.append(current.strip())
        if not chunks:
            chunks = [cleaned[:target_chunk_size].strip()]
        return [chunk for chunk in chunks if chunk]

    def _summarize_document_deep(
        self,
        *,
        text: str,
        instruction: str,
        title: str,
        page_count: int = 0,
        learning_hint: str = "",
        capture_trace: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        chunks = self._chunk_text_for_summary(text, target_chunk_size=4500, max_chunks=6)
        if len(chunks) <= 1:
            return self._summarize_text(
                text,
                instruction=instruction,
                title=title,
                learning_hint=learning_hint,
                style="document",
                content_limit=28000,
                deep=True,
                cache_scope="media:document-summary:deep",
                capture_trace=capture_trace,
            )

        chunk_notes: list[str] = []
        doc_placeholder = t("skills.document_placeholder")
        resolved_title = title or doc_placeholder
        for index, chunk in enumerate(chunks, start=1):
            chunk_prompt = t("skills.media_doc_chunk_prompt", index=index, total=len(chunks), title=resolved_title)
            chunk_instruction = instruction.strip()
            if chunk_instruction:
                chunk_instruction = f"{chunk_instruction}\n\n{chunk_prompt}"
            else:
                chunk_instruction = chunk_prompt
            part_label = t("skills.media_doc_part_label", index=index)
            chunk_summary = self._summarize_text(
                chunk,
                instruction=chunk_instruction,
                title=f"{title} - {part_label}" if title else part_label,
                learning_hint=learning_hint,
                style="document",
                content_limit=10000,
                deep=False,
                cache_scope="media:document-summary:deep-chunk",
            )
            if chunk_summary.strip():
                chunk_notes.append(t("skills.media_doc_section_label", index=index, content=chunk_summary.strip()))

        merged_notes = "\n\n".join(chunk_notes).strip()
        if not merged_notes:
            return self._summarize_text(
                text,
                instruction=instruction,
                title=title,
                learning_hint=learning_hint,
                style="document",
                content_limit=28000,
                deep=True,
                cache_scope="media:document-summary:deep",
            )

        merge_prompt = t("skills.media_doc_merge_prompt", title=resolved_title)
        merge_instruction = instruction.strip() or merge_prompt
        if instruction.strip():
            merge_instruction = f"{instruction.strip()}\n\n{merge_prompt}"
        return self._summarize_text(
            merged_notes,
            instruction=merge_instruction,
            title=title,
            learning_hint=learning_hint,
            style="document",
            content_limit=12000,
            deep=True,
            cache_scope="media:document-summary:deep-merge",
            capture_trace=capture_trace,
        )

    @staticmethod
    def _is_deep_document_question_request(*, question: str, text: str, page_count: int = 0) -> bool:
        normalized_question = normalize_spaces((question or "").lower())
        normalized_text = normalize_spaces((text or "").lower())
        cues = (
            "phân tích sâu",
            "phân tích kỹ",
            "kỹ hơn",
            "chi tiết hơn",
            "đầy đủ hơn",
            "giải thích kỹ",
            "bóc tách",
            "nêu rõ",
            "từng phần",
            "từng mục",
            "chi tiết",
            "deep",
        )
        if any(cue in normalized_question for cue in cues):
            return True
        if page_count >= 6:
            return True
        if len(normalized_text) >= 12000:
            return True
        return False

    def _answer_question_deep(
        self,
        *,
        question: str,
        context: str,
        title: str = "",
        learning_hint: str = "",
        capture_trace: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        chunks = self._chunk_text_for_summary(context, target_chunk_size=5000, max_chunks=8)
        if len(chunks) <= 1:
            return self._answer_question(
                question=question,
                context=context,
                title=title,
                learning_hint=learning_hint,
                capture_trace=capture_trace,
            )

        chunk_answers: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            chunk_result, _chunk_provider = self._invoke_analysis(
                [
                    SystemMessage(
                        content=t("skills.media_doc_long_chunk_system")
                    ),
                    HumanMessage(
                        content=t(
                            "skills.media_doc_long_chunk_human",
                            title=title or t("skills.unknown"),
                            index=index,
                            total=len(chunks),
                            question=question.strip(),
                            content=compact_text(chunk, limit=9000),
                        )
                    ),
                ],
                scope="media:document-qa:deep-chunk",
            )
            chunk_answer = normalize_spaces(str(chunk_result.content).strip())
            if chunk_answer and "KHONG_CO_THONG_TIN" not in chunk_answer.upper():
                part_label = t("skills.media_doc_part_label", index=index)
                chunk_answers.append(f"{part_label.capitalize()}: {chunk_answer}")

        if not chunk_answers:
            return self._answer_question(
                question=question,
                context=context,
                title=title,
                learning_hint=learning_hint,
                capture_trace=capture_trace,
            )

        merged_answers = "\n".join(chunk_answers)
        final_result, provider_used = self._invoke_analysis(
            [
                SystemMessage(
                    content=t("skills.media_doc_long_final")
                ),
                HumanMessage(
                    content=t(
                        "skills.media_doc_long_merge_human",
                        title=title or t("skills.unknown"),
                        question=question.strip(),
                        answers=merged_answers,
                    )
                ),
            ],
            scope="media:document-qa:deep-final",
        )
        answer_text = str(final_result.content).strip()
        if capture_trace:
            return answer_text, self._analysis_trace(final_result, scope="media:document-qa:deep-final", provider_used=provider_used)
        return answer_text

    def _answer_question(
        self,
        *,
        question: str,
        context: str,
        title: str = "",
        learning_hint: str = "",
        capture_trace: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        content = compact_text(context, limit=18000)
        prompt = question.strip() or t("skills.media_doc_qa_normal_prompt")
        if learning_hint.strip():
            prompt = f"{prompt}\n\n" + t("skills.media_notes_header", hint=learning_hint.strip())
        result, provider_used = self._invoke_analysis(
            [
                SystemMessage(
                    content=t("skills.media_doc_qa_system")
                ),
                HumanMessage(
                    content=t(
                        "skills.media_doc_qa_normal_human",
                        title=title or t("skills.unknown"),
                        question=prompt,
                        content=content,
                    )
                ),
            ],
            scope="media:document-qa:normal",
        )
        answer_text = str(result.content).strip()
        if capture_trace:
            return answer_text, self._analysis_trace(result, scope="media:document-qa:normal", provider_used=provider_used)
        return answer_text

    def _extract_json_fields(
        self,
        *,
        text: str,
        title: str = "",
        instruction: str = "",
        learning_hint: str = "",
        capture_trace: bool = False,
    ) -> dict[str, Any] | tuple[dict[str, Any], dict[str, Any]]:
        content = compact_text(text, limit=18000)
        structured = parse_structured_fields(content)
        prompt = instruction.strip() or t("skills.media_doc_extract_fields_prompt")
        if learning_hint.strip():
            prompt = f"{prompt}\n\n" + t("skills.media_notes_header", hint=learning_hint.strip())
        result, provider_used = self._invoke_analysis(
            [
                SystemMessage(
                    content=t("skills.media_doc_extract_fields_system")
                ),
                HumanMessage(
                    content=t(
                        "skills.media_doc_extract_fields_human",
                        title=title or t("skills.unknown"),
                        instruction=prompt,
                        content=content,
                    )
                ),
            ],
            scope="media:document-fields",
        )
        raw = str(result.content).strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"summary": raw, "fields": {}}
        if "fields" not in parsed or not isinstance(parsed["fields"], dict):
            parsed["fields"] = {}
        parsed["fields"] = {**structured, **parsed["fields"]}
        if "summary" not in parsed or not str(parsed["summary"]).strip():
            parsed["summary"] = self._summarize_text(content, instruction=prompt, title=title)
        if capture_trace:
            return parsed, self._analysis_trace(result, scope="media:document-fields", provider_used=provider_used)
        return parsed

    @staticmethod
    def _non_empty_field_items(fields: dict[str, Any]) -> list[tuple[str, Any]]:
        items: list[tuple[str, Any]] = []
        for key, value in (fields or {}).items():
            if isinstance(value, list) and value:
                items.append((key, value))
            elif isinstance(value, str) and value.strip():
                items.append((key, value.strip()))
            elif value not in (None, "", [], {}):
                items.append((key, value))
        return items

    @staticmethod
    def _strip_markdown_noise(text: str) -> str:
        cleaned = str(text or "").strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned

    @classmethod
    def _split_readable_chunks(cls, text: str, *, max_items: int = 4, prefer_line_breaks: bool = True) -> list[str]:
        cleaned = cls._strip_markdown_noise(text)
        if not cleaned:
            return []

        raw_lines = [normalize_spaces(line) for line in cleaned.splitlines() if normalize_spaces(line)]
        if prefer_line_breaks and len(raw_lines) >= 2:
            line_chunks = [
                normalize_spaces(re.sub(r"^(?:[-*•]|\d+[.)])\s*", "", line))
                for line in raw_lines
            ]
            line_chunks = [chunk for chunk in line_chunks if chunk]
            average_length = (sum(len(chunk) for chunk in line_chunks) / len(line_chunks)) if line_chunks else 0
            if len(line_chunks) >= 2 and average_length >= 30:
                return line_chunks[:max_items]

        sentence_chunks = [
            normalize_spaces(part)
            for part in re.split(r"(?<=[.!?。！？])\s+", normalize_spaces(cleaned))
            if normalize_spaces(part)
        ]
        if len(sentence_chunks) >= 2:
            return sentence_chunks[:max_items]

        fallback_chunks = [
            normalize_spaces(part)
            for part in re.split(r"[;\n]+", cleaned)
            if normalize_spaces(part)
        ]
        return fallback_chunks[:max_items] if fallback_chunks else [cleaned[:180].strip()]

    @classmethod
    def _format_readable_sectioned_text(
        cls,
        *,
        heading: str,
        text: str,
        labels: list[str],
        max_items: int,
        prefer_line_breaks: bool = True,
    ) -> str:
        chunks = cls._split_readable_chunks(text, max_items=max_items, prefer_line_breaks=prefer_line_breaks)
        if not chunks:
            return str(text or "").strip()

        lines = [heading.strip()]
        for index, label in enumerate(labels):
            if index >= len(chunks):
                break
            value = normalize_spaces(chunks[index])
            if value:
                lines.append(f"- {label}: {value}")

        remaining = chunks[len(labels) :]
        if remaining:
            tail = " ".join(normalize_spaces(item) for item in remaining if normalize_spaces(item))
            if tail:
                lines.append(f"- Ghi chú: {tail}")

        return "\n".join(lines).strip()

    @staticmethod
    def _clean_summary_chunk(value: str, *, title: str = "") -> str:
        chunk = normalize_spaces(value)
        if not chunk:
            return ""
        redundant_prefixes = [
            r"^tóm tắt\s+",
            r"^mô tả ảnh\s+",
            r"^mô tả\s+",
            r"^summary\s+",
        ]
        if title:
            redundant_prefixes.append(rf"^tóm tắt\s+{re.escape(title)}\s*[:\-–]?\s*")
            redundant_prefixes.append(rf"^{re.escape(title)}\s*[:\-–]?\s*")
        chunk = re.sub(
            r"^(?:Mục tiêu|Nội dung chính|Yêu cầu(?:/đầu việc)?(?:\s*nổi bật)?|Đầu ra(?:\s*/\s*|\s+hoặc\s+)?lưu ý|Tổng quan|Chi tiết nổi bật|Ghi chú)\s*:\s*",
            "",
            chunk,
            flags=re.IGNORECASE,
        )
        for pattern in redundant_prefixes:
            cleaned = re.sub(pattern, "", chunk, flags=re.IGNORECASE)
            if cleaned != chunk:
                chunk = cleaned
        return normalize_spaces(chunk)

    @classmethod
    def _format_document_summary_text(cls, *, title: str, text: str, deep: bool = False) -> str:
        chunks = cls._split_readable_chunks(text, max_items=8, prefer_line_breaks=True)
        cleaned_chunks = [cls._clean_summary_chunk(chunk, title=title) for chunk in chunks]
        cleaned_chunks = [chunk for chunk in cleaned_chunks if chunk]

        if cleaned_chunks and (cleaned_chunks[0].lower().startswith("tóm tắt") or cleaned_chunks[0].lower().startswith("summary")):
            cleaned_chunks = cleaned_chunks[1:]
        if title:
            cleaned_chunks = [chunk for chunk in cleaned_chunks if chunk.lower() != title.lower()]

        if not cleaned_chunks:
            return str(text or "").strip()

        deep_mode = deep or len(cleaned_chunks) > 4
        labels = t("skills.media_doc_summary_labels_deep") if deep_mode else t("skills.media_doc_summary_labels_normal")
        if not isinstance(labels, list):
            labels = (
                ["Tổng quan", "Mục tiêu", "Nội dung chính", "Chi tiết quan trọng", "Ràng buộc / yêu cầu nổi bật", "Đầu ra / lưu ý"]
                if deep_mode
                else ["Mục tiêu", "Nội dung chính", "Yêu cầu nổi bật", "Đầu ra / lưu ý"]
            )
        summary_title = t("skills.web_summary_title", title=title or t("skills.document_placeholder"))
        lines = [summary_title]
        for index, label in enumerate(labels):
            if index >= len(cleaned_chunks):
                break
            lines.append(f"- {label}: {cleaned_chunks[index]}")

        if len(cleaned_chunks) > len(labels):
            tail = " ".join(cleaned_chunks[len(labels):]).strip()
            if tail:
                notes_label = t("skills.media_doc_notes_label", default="Ghi chú")
                lines.append(f"- {notes_label}: {tail}")

        return "\n".join(lines).strip()

    @staticmethod
    def _build_document_page_refs(meta: dict[str, Any], *, question: str = "", limit: int = 4) -> list[dict[str, Any]]:
        raw_refs = meta.get("page_refs") or meta.get("pageRefs") or []
        if not isinstance(raw_refs, list) or not raw_refs:
            return []

        question_tokens = [
            token
            for token in re.split(r"\W+", normalize_spaces(question).lower())
            if len(token) >= 4
        ]
        scored: list[tuple[int, dict[str, Any]]] = []
        for ref in raw_refs:
            if not isinstance(ref, dict):
                continue
            page = ref.get("page") or ref.get("page_number") or ref.get("pageNumber")
            snippet = normalize_spaces(str(ref.get("snippet") or ref.get("text") or ref.get("content") or ""))
            if not page or not snippet:
                continue
            score = 0
            lowered = snippet.lower()
            for token in question_tokens:
                if token in lowered:
                    score += 1
            scored.append(
                (
                    score,
                    {
                        "page": int(page),
                        "snippet": snippet[:220],
                        "score": score,
                    },
                )
            )
        if not scored:
            scored = [
                (
                    0,
                    {
                        "page": int(ref.get("page") or ref.get("page_number") or ref.get("pageNumber") or 0),
                        "snippet": normalize_spaces(str(ref.get("snippet") or ref.get("text") or ref.get("content") or ""))[:220],
                        "score": 0,
                    },
                )
                for ref in raw_refs
                if isinstance(ref, dict) and (ref.get("page") or ref.get("page_number") or ref.get("pageNumber"))
            ]
        scored.sort(key=lambda item: (item[0], item[1]["page"]), reverse=True)
        return [item[1] for item in scored[: max(1, limit)] if item[1].get("page")]

    @staticmethod
    def _format_page_refs_text(page_refs: list[dict[str, Any]], *, label: str = "Trang tham chiếu", limit: int = 4) -> str:
        lines: list[str] = []
        for ref in page_refs[:limit]:
            page = ref.get("page")
            snippet = normalize_spaces(str(ref.get("snippet") or ""))
            if not page:
                continue
            if snippet:
                lines.append(f"{page}: {snippet}")
            else:
                lines.append(str(page))
        if not lines:
            return ""
        return f"- {label}: " + "; ".join(lines)

    def _describe_image_locally(self, *, image_bytes: bytes, title: str = "") -> str:
        stats = image_basic_stats(image_bytes)
        ocr_text = extract_text_from_image_bytes(image_bytes, ocr_langs=self.settings.ocr_languages)
        attached_placeholder = t("skills.attached_placeholder", default="đính kèm")
        lines = [t("skills.media_image_describe_local_title", title=title or attached_placeholder)]
        if ocr_text:
            preview = compact_text(ocr_text, limit=280)
            ocr_label = t("skills.media_image_describe_local_ocr_label", default="Chữ đọc được")
            lines.append(f"- {ocr_label}: {preview}")
            lines.append(t("skills.media_image_ocr_fallback_note"))
        else:
            lines.append("- " + t("skills.media_image_describe_local_empty_ocr"))
            basic_stats = t(
                "skills.media_image_describe_local_basic_stats",
                width=stats.get("width"),
                height=stats.get("height"),
                quality=stats.get("estimated_quality"),
            )
            lines.append(f"- {basic_stats}")
            lines.append(t("skills.media_image_vision_fallback_note"))
        return "\n".join(lines).strip()

    def _format_image_fields_text(self, *, summary: str, fields: dict[str, Any], title: str = "") -> str:
        attached_placeholder = t("skills.attached_placeholder", default="đính kèm")
        lines = [t("skills.media_image_info_title", title=title or attached_placeholder)]
        if summary.strip():
            lines.append(f"- {t('skills.summary_label', summary=summary.strip())}")
        for key, value in self._non_empty_field_items(fields)[:6]:
            if isinstance(value, list):
                rendered = ", ".join(str(item).strip() for item in value[:5] if str(item).strip())
            else:
                rendered = str(value).strip()
            if rendered:
                lines.append(f"- {key}: {rendered}")
        if len(lines) == 1:
            lines.append("- " + t("skills.media_image_fields_empty"))
        return "\n".join(lines).strip()

    def _decode_file(self, file_base64: str) -> bytes:
        if not file_base64:
            return b""
        encoded = str(file_base64).strip()
        estimated_size = (len(encoded) * 3) // 4
        max_bytes = max(1024, int(self.settings.media_max_input_bytes))
        if estimated_size > max_bytes:
            raise ValueError("Media input is larger than the configured limit.")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("Media input is not valid base64 data.") from exc
        if len(data) > max_bytes:
            raise ValueError("Media input is larger than the configured limit.")
        return data

    def _load_media(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str) -> MediaBytes:
        data = self._decode_file(file_base64)
        if not data:
            raise ValueError(t("skills.media_unprocessed"))
        safe_name = Path(str(file_name or "attachment")).name or "attachment"
        return MediaBytes(file_name=safe_name, mime_type=mime_type, attachment_kind=attachment_kind, data=data)

    def image_ocr(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        text = extract_text_from_image_bytes(media.data, ocr_langs=self.settings.ocr_languages)
        result = MediaResult(
            tool="image_ocr",
            text=text or t("skills.media_image_ocr_failed"),
            data={
                "ocr_text": text,
                "stats": image_basic_stats(media.data),
            },
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "photo",
            warnings=[] if text else ["ocr_empty"],
        )
        self._record_learning_event(
            tool="image_ocr",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace={},
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="image OCR",
        )
        return result

    def image_describe(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        warnings: list[str] = []
        learning_hint = self._learning_guidance_text(tool="image_describe", attachment_kind=media.attachment_kind)
        vision_prompt = instruction.strip()
        if learning_hint.strip():
            vision_prompt = "\n\n".join(part for part in [vision_prompt, f"Ghi chú học được:\n{learning_hint.strip()}"] if part).strip()
        if self.groq.enabled:
            try:
                description = self.groq.describe_image(
                    image_bytes=media.data,
                    mime_type=media.mime_type or "image/png",
                    model=self.settings.groq_vision_model,
                    prompt=vision_prompt,
                )
            except Exception:
                description = self._describe_image_locally(image_bytes=media.data, title=media.file_name)
                warnings.append("vision_fallback_local")
        else:
            description = self._describe_image_locally(image_bytes=media.data, title=media.file_name)
            warnings.append("vision_unavailable")
        formatted_description = self._format_readable_sectioned_text(
            heading=f"Mô tả ảnh {media.file_name or 'đính kèm'}",
            text=description,
            labels=["Tổng quan", "Chi tiết nổi bật", "Ghi chú"],
            max_items=3,
            prefer_line_breaks=False,
        )
        result = MediaResult(
            tool="image_describe",
            text=formatted_description,
            data={
                "image": image_basic_stats(media.data),
                "description": description,
            },
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "photo",
            warnings=warnings,
            trace={},
        )
        self._record_learning_event(
            tool="image_describe",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="image describe",
        )
        return result

    def image_extract_fields(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        warnings: list[str] = []
        trace: dict[str, Any] = {}
        learning_hint = self._learning_guidance_text(tool="image_extract_fields", attachment_kind=media.attachment_kind)
        field_instruction = instruction.strip()
        if learning_hint.strip():
            field_instruction = "\n\n".join(
                part for part in [field_instruction, f"Ghi chú học được:\n{learning_hint.strip()}"] if part
            ).strip()
        if self.groq.enabled:
            try:
                parsed = self.groq.extract_image_fields(
                    image_bytes=media.data,
                    mime_type=media.mime_type or "image/png",
                    model=self.settings.groq_vision_model,
                    prompt=field_instruction,
                )
                fields = parsed.get("fields") if isinstance(parsed.get("fields"), dict) else {}
                summary = str(parsed.get("summary") or "").strip()
            except Exception:
                ocr_text = extract_text_from_image_bytes(media.data, ocr_langs=self.settings.ocr_languages)
                fields = parse_structured_fields(ocr_text)
                summary_result = self._summarize_text(
                    ocr_text,
                    instruction=field_instruction,
                    title=file_name,
                    learning_hint=learning_hint,
                    capture_trace=True,
                ) if ocr_text else ""
                if isinstance(summary_result, tuple):
                    summary, trace = summary_result
                else:
                    summary, trace = summary_result, {}
                parsed = {"summary": summary, "fields": fields}
                warnings.append("vision_fallback_local")
        else:
            ocr_text = extract_text_from_image_bytes(media.data, ocr_langs=self.settings.ocr_languages)
            fields = parse_structured_fields(ocr_text)
            summary_result = self._summarize_text(
                ocr_text,
                instruction=field_instruction,
                title=file_name,
                learning_hint=learning_hint,
                capture_trace=True,
            ) if ocr_text else ""
            if isinstance(summary_result, tuple):
                summary, trace = summary_result
            else:
                summary, trace = summary_result, {}
            parsed = {"summary": summary, "fields": fields}
            warnings.append("vision_unavailable")
        text = self._format_image_fields_text(summary=summary, fields=fields, title=media.file_name)
        result = MediaResult(
            tool="image_extract_fields",
            text=text,
            data=parsed,
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "photo",
            warnings=warnings,
            trace=trace,
        )
        self._record_learning_event(
            tool="image_extract_fields",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="image extract fields",
        )
        return result

    def document_extract_text(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        extracted = extract_document_text(media.data, file_name=media.file_name, mime_type=media.mime_type, ocr_langs=self.settings.ocr_languages)
        result = MediaResult(
            tool="document_extract_text",
            text=extracted.text or t("skills.media_document_ocr_failed"),
            data={"document": extracted.meta, "text": extracted.text},
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "document",
            warnings=[] if extracted.text else ["document_text_empty"],
        )
        self._record_learning_event(
            tool="document_extract_text",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace={},
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="document extract text",
        )
        return result

    def document_summarize(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        extracted = extract_document_text(media.data, file_name=media.file_name, mime_type=media.mime_type, ocr_langs=self.settings.ocr_languages)
        page_count = int(extracted.meta.get("pages") or 0)
        learning_hint = self._learning_guidance_text(tool="document_summarize", attachment_kind=media.attachment_kind)
        summary_instruction = instruction.strip()
        if learning_hint.strip():
            summary_instruction = "\n\n".join(
                part for part in [summary_instruction, t("skills.media_notes_header", hint=learning_hint.strip())] if part
            ).strip()
        deep_summary = self._is_deep_document_summary_request(
            instruction=summary_instruction,
            text=extracted.text,
            page_count=page_count,
        )
        if deep_summary:
            summary_result = self._summarize_document_deep(
                text=extracted.text,
                instruction=summary_instruction,
                title=media.file_name,
                page_count=page_count,
                learning_hint=learning_hint,
                capture_trace=True,
            )
        else:
            summary_result = self._summarize_text(
                extracted.text,
                instruction=summary_instruction,
                title=media.file_name,
                style="document",
                learning_hint=learning_hint,
                capture_trace=True,
            )
        if isinstance(summary_result, tuple):
            summary, trace = summary_result
        else:
            summary, trace = summary_result, {}
        formatted_summary = self._format_document_summary_text(title=media.file_name, text=summary, deep=deep_summary)
        page_refs = self._build_document_page_refs(extracted.meta, limit=4)
        refs_text = self._format_page_refs_text(page_refs, label=t("skills.media_doc_page_refs_label", default="Trang tham chiếu"), limit=4)
        if refs_text:
            formatted_summary = "\n".join(part for part in [formatted_summary, refs_text] if part).strip()
        result = MediaResult(
            tool="document_summarize",
            text=formatted_summary or t("skills.media_document_summary_failed"),
            data={"document": {**extracted.meta, "page_refs": page_refs}, "text": extracted.text, "summary": summary, "formatted_summary": formatted_summary},
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "document",
            trace={"llm": trace} if trace else {},
        )
        self._record_learning_event(
            tool="document_summarize",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="document summarize",
        )
        return result

    def document_search_answer(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, question: str = "", instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        extracted = extract_document_text(media.data, file_name=media.file_name, mime_type=media.mime_type, ocr_langs=self.settings.ocr_languages)
        page_count = int(extracted.meta.get("pages") or 0)
        learning_hint = self._learning_guidance_text(tool="document_search_answer", attachment_kind=media.attachment_kind)
        question_text = (question or instruction).strip()
        if learning_hint.strip():
            question_text = "\n\n".join(
                part for part in [question_text, t("skills.media_notes_header", hint=learning_hint.strip())] if part
            ).strip()
        deep_answer = self._is_deep_document_question_request(
            question=question_text,
            text=extracted.text,
            page_count=page_count,
        )
        if deep_answer:
            answer_result = self._answer_question_deep(
                question=question_text,
                context=extracted.text,
                title=media.file_name,
                learning_hint=learning_hint,
                capture_trace=True,
            )
        else:
            answer_result = self._answer_question(
                question=question_text,
                context=extracted.text,
                title=media.file_name,
                learning_hint=learning_hint,
                capture_trace=True,
            )
        if isinstance(answer_result, tuple):
            answer, trace = answer_result
        else:
            answer, trace = answer_result, {}
        page_refs = self._build_document_page_refs(extracted.meta, question=question or instruction, limit=4)
        refs_text = self._format_page_refs_text(page_refs, label=t("skills.media_doc_page_refs_label", default="Trang tham chiếu"), limit=4)
        if refs_text and refs_text not in answer:
            answer = "\n".join(part for part in [answer, refs_text] if part).strip()
        result = MediaResult(
            tool="document_search_answer",
            text=answer or t("skills.media_doc_qa_failed"),
            data={"document": {**extracted.meta, "page_refs": page_refs}, "text": extracted.text, "question": question or instruction, "answer": answer},
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "document",
            trace={"llm": trace} if trace else {},
        )
        self._record_learning_event(
            tool="document_search_answer",
            request_text=question or instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="document search answer",
        )
        return result

    def document_extract_fields(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        extracted = extract_document_text(media.data, file_name=media.file_name, mime_type=media.mime_type, ocr_langs=self.settings.ocr_languages)
        learning_hint = self._learning_guidance_text(tool="document_extract_fields", attachment_kind=media.attachment_kind)
        field_instruction = instruction.strip()
        if learning_hint.strip():
            field_instruction = "\n\n".join(
                part for part in [field_instruction, f"Ghi chú học được:\n{learning_hint.strip()}"] if part
            ).strip()
        parsed_result = self._extract_json_fields(
            text=extracted.text,
            title=media.file_name,
            instruction=field_instruction,
            learning_hint=learning_hint,
            capture_trace=True,
        )
        if isinstance(parsed_result, tuple):
            parsed, trace = parsed_result
        else:
            parsed, trace = parsed_result, {}
        result = MediaResult(
            tool="document_extract_fields",
            text=str(parsed.get("summary") or "Mia đã trích xuất các trường chính từ tài liệu."),
            data={"document": {**extracted.meta, "page_refs": self._build_document_page_refs(extracted.meta, limit=4)}, "text": extracted.text, **parsed},
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "document",
            trace={"llm": trace} if trace else {},
        )
        self._record_learning_event(
            tool="document_extract_fields",
            request_text=instruction,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="document extract fields",
        )
        return result

    def audio_transcribe(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, language: str = "", instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        transcribed = self.groq.transcribe_audio(
            file_bytes=media.data,
            file_name=media.file_name or "audio.bin",
            mime_type=media.mime_type or "audio/mpeg",
            model=self.settings.groq_stt_model,
            language=language.strip(),
            prompt=instruction,
        )
        result = MediaResult(
            tool="audio_transcribe",
            text=transcribed.text or t("skills.media_audio_transcribe_empty"),
            data=transcribed.data,
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "audio",
            warnings=[] if transcribed.text else ["transcription_empty"],
        )
        self._record_learning_event(
            tool="audio_transcribe",
            request_text=instruction or language,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace={},
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="audio transcription",
        )
        return result

    def audio_summarize(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", language: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        transcribed = self.audio_transcribe(
            file_base64=file_base64,
            file_name=file_name,
            mime_type=mime_type,
            attachment_kind=attachment_kind,
            language=language,
            instruction=instruction,
            request_id=request_id,
            chat_id=chat_id,
        )
        learning_hint = self._learning_guidance_text(tool="audio_summarize", attachment_kind=attachment_kind)
        summary_instruction = instruction.strip()
        if learning_hint.strip():
            summary_instruction = "\n\n".join(
                part for part in [summary_instruction, t("skills.media_notes_header", hint=learning_hint.strip())] if part
            ).strip()
        summary_result = self._summarize_text(
            transcribed.text,
            instruction=summary_instruction,
            title=file_name,
            learning_hint=learning_hint,
            capture_trace=True,
        )
        if isinstance(summary_result, tuple):
            summary, trace = summary_result
        else:
            summary, trace = summary_result, {}
        result = MediaResult(
            tool="audio_summarize",
            text=summary or t("skills.media_audio_summarize_empty"),
            data={**transcribed.data, "transcript": transcribed.text, "summary": summary},
            file_name=file_name,
            mime_type=mime_type,
            attachment_kind=attachment_kind or "audio",
            trace={"llm": trace} if trace else {},
        )
        self._record_learning_event(
            tool="audio_summarize",
            request_text=instruction or language,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="audio summarize",
        )
        return result

    def video_transcribe(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, language: str = "", instruction: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        media = self._load_media(file_base64=file_base64, file_name=file_name, mime_type=mime_type, attachment_kind=attachment_kind)
        transcribed = self.groq.transcribe_audio(
            file_bytes=media.data,
            file_name=media.file_name or "video.bin",
            mime_type=media.mime_type or "video/mp4",
            model=self.settings.groq_stt_model,
            language=language.strip(),
            prompt=instruction,
        )
        result = MediaResult(
            tool="video_transcribe",
            text=transcribed.text or t("skills.media_video_transcribe_empty"),
            data=transcribed.data,
            file_name=media.file_name,
            mime_type=media.mime_type,
            attachment_kind=media.attachment_kind or "video",
            warnings=[] if transcribed.text else ["transcription_empty"],
        )
        self._record_learning_event(
            tool="video_transcribe",
            request_text=instruction or language,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace={},
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="video transcription",
        )
        return result

    def video_summarize(self, *, file_base64: str, file_name: str, mime_type: str, attachment_kind: str, instruction: str = "", language: str = "", request_id: str = "", chat_id: str = "") -> MediaResult:
        transcribed = self.video_transcribe(
            file_base64=file_base64,
            file_name=file_name,
            mime_type=mime_type,
            attachment_kind=attachment_kind,
            language=language,
            instruction=instruction,
            request_id=request_id,
            chat_id=chat_id,
        )
        learning_hint = self._learning_guidance_text(tool="video_summarize", attachment_kind=attachment_kind)
        summary_instruction = instruction.strip()
        if learning_hint.strip():
            summary_instruction = "\n\n".join(
                part for part in [summary_instruction, t("skills.media_notes_header", hint=learning_hint.strip())] if part
            ).strip()
        summary_result = self._summarize_text(
            transcribed.text,
            instruction=summary_instruction,
            title=file_name,
            learning_hint=learning_hint,
            capture_trace=True,
        )
        if isinstance(summary_result, tuple):
            summary, trace = summary_result
        else:
            summary, trace = summary_result, {}
        result = MediaResult(
            tool="video_summarize",
            text=summary or t("skills.media_video_summarize_empty"),
            data={**transcribed.data, "transcript": transcribed.text, "summary": summary},
            file_name=file_name,
            mime_type=mime_type,
            attachment_kind=attachment_kind or "video",
            trace={"llm": trace} if trace else {},
        )
        self._record_learning_event(
            tool="video_summarize",
            request_text=instruction or language,
            final_text=result.text,
            attachment_kind=result.attachment_kind,
            trace=result.trace,
            warnings=result.warnings,
            file_name=result.file_name,
            mime_type=result.mime_type,
            request_id=request_id,
            chat_id=chat_id,
            notes="video summarize",
        )
        return result

    def tts_speak(self, *, text: str, model: str = "", voice: str = "", response_format: str = "mp3", request_id: str = "", chat_id: str = "") -> tuple[bytes, str, str]:
        spoken_text = re.sub(r"\s+", " ", text or "").strip()
        if not spoken_text:
            raise ValueError(t("skills.media_tts_empty"))
        audio_bytes, content_type = self.groq.speak(
            text=spoken_text,
            model=model or self.settings.groq_tts_model,
            voice=voice or self.settings.groq_tts_voice,
            response_format=response_format or self.settings.groq_tts_format,
        )
        filename = f"mia-tts.{self.settings.groq_tts_format or 'mp3'}"
        self._record_learning_event(
            tool="tts_speak",
            request_text=spoken_text,
            final_text=spoken_text,
            attachment_kind="tts",
            trace={},
            warnings=[],
            file_name=filename,
            mime_type=content_type or "audio/mpeg",
            request_id=request_id,
            chat_id=chat_id,
            notes="tts speak",
        )
        return audio_bytes, content_type, filename
