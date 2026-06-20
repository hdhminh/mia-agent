from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from agent.i18n import t


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_json(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    text = str(value).strip()
    return [text] if text else []


def _hash_digest(*parts: str) -> str:
    payload = "|".join(_normalize_text(part) for part in parts if _normalize_text(part))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


def _extract_llm_trace(trace: Any) -> dict[str, Any]:
    if not isinstance(trace, dict):
        return {}
    llm_trace = trace.get("llm")
    if isinstance(llm_trace, dict):
        return llm_trace
    tool_summary = trace.get("tool_summary")
    if isinstance(tool_summary, dict):
        return tool_summary
    return {}


def _first_int(*values: Any) -> int:
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return int(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return 0


def _first_float(*values: Any) -> float:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _normalize_verdict(value: str) -> str:
    normalized = _normalize_text(value).lower()
    normalized = normalized.replace("đ", "d")
    aliases = {
        "up": "up",
        "yes": "up",
        "good": "up",
        "ok": "up",
        "down": "down",
        "no": "down",
        "bad": "down",
        "shorter": "shorter",
        "ngan hon": "shorter",
        "gon hon": "shorter",
        "longer": "longer",
        "dai hon": "longer",
        "deeper": "deeper",
        "ky hon": "deeper",
        "chi tiet hon": "deeper",
        "clearer": "clearer",
        "de hieu hon": "clearer",
        "readable": "readable",
        "de doc hon": "readable",
        "correct": "correct",
        "sai": "incorrect",
        "incorrect": "incorrect",
    }
    return aliases.get(normalized, normalized)


def _feedback_style_payload(verdict: str, comment: str, current_text: str, correction_text: str) -> dict[str, Any] | None:
    normalized_verdict = _normalize_verdict(verdict)
    comment_text = _normalize_text(comment)
    correction = _normalize_text(correction_text)
    current = _normalize_text(current_text)
    joined = " ".join(part for part in [normalized_verdict, comment_text, correction, current] if part).lower()

    if normalized_verdict in {"shorter", "longer", "deeper", "clearer", "readable"}:
        topic = "style_short" if normalized_verdict == "shorter" else "style_deep" if normalized_verdict in {"longer", "deeper"} else "format_readable"
        return {
            "scope": "document" if "file" in joined or "document" in joined else "general",
            "topic": topic,
            "title": {
                "style_short": "Response style preference: shorter",
                "style_deep": "Response style preference: deeper",
                "format_readable": "Readable formatting preference",
            }[topic],
            "prompt_hint": {
                "style_short": t("learning.style_short"),
                "style_deep": t("learning.style_deep"),
                "format_readable": t("learning.prompt_hint_format_readable"),
            }[topic],
            "memory_hint": {
                "style_short": "Keep responses shorter when the user asks for it.",
                "style_deep": "Prefer deeper, more complete bullets for this user.",
                "format_readable": "Use readable sectioned formatting for document outputs.",
            }[topic],
            "examples": [],
            "confidence": 0.75,
        }

    if normalized_verdict in {"incorrect", "down"} or "sai" in joined or "chua dung" in joined or "chưa đúng" in joined:
        if any(token in joined for token in ("anh", "document", "file", "pdf", "tai lieu", "tài liệu")):
            return {
                "scope": "document",
                "topic": "followup",
                "title": "Document follow-up clarification",
                "prompt_hint": t("learning.prompt_hint_doc"),
                "memory_hint": "Follow up on the most recent document context before answering.",
                "examples": [],
                "confidence": 0.7,
            }
        if any(token in joined for token in ("anh", "image", "anh nay", "ảnh này", "photo", "ảnh", "ocr")):
            return {
                "scope": "image",
                "topic": "routing",
                "title": "Image routing hint",
                "prompt_hint": t("learning.prompt_hint_image"),
                "memory_hint": "Route attached images to image_describe/image_ocr first.",
                "examples": [],
                "confidence": 0.7,
            }

    if comment_text:
        comment_lower = comment_text.lower()
        if any(cue in comment_lower for cue in ("ngắn hơn", "ngan hon", "gọn hơn", "gon hon", "ít chữ", "it chu")):
            return {
                "scope": "general",
                "topic": "style_short",
                "title": "Response style preference: shorter",
                "prompt_hint": t("learning.style_short"),
                "memory_hint": "Keep responses shorter when the user asks for it.",
                "examples": [],
                "confidence": 0.7,
            }
        if any(cue in comment_lower for cue in ("dài hơn", "dai hon", "chi tiết hơn", "chi tiet hon", "kỹ hơn", "ky hon")):
            return {
                "scope": "document",
                "topic": "style_deep",
                "title": "Response style preference: deeper",
                "prompt_hint": t("learning.style_deep"),
                "memory_hint": "Prefer deeper, more complete bullets for this user.",
                "examples": [],
                "confidence": 0.7,
            }

    return None


def should_promote_candidate(
    *,
    support_count: int,
    confidence: float,
    has_feedback: bool = False,
    allow_single_support: bool = False,
) -> tuple[bool, str]:
    if confidence >= 0.8 and support_count >= 2:
        return True, "high confidence and repeated support"
    if support_count >= 3:
        return True, "enough repeated support"
    if allow_single_support and support_count >= 1 and has_feedback:
        return True, "explicit feedback override"
    if has_feedback and support_count >= 2:
        return True, "feedback-backed support"
    return False, "insufficient support"


def build_learning_guidance_text(rows: list[dict[str, Any]], *, limit: int = 5) -> str:
    if not rows:
        return ""

    lines = ["Ghi chú học được từ các lượt trước:"]
    count = 0
    for row in rows:
        hint = _normalize_text(row.get("prompt_hint") or row.get("memory_hint") or "")
        if not hint:
            continue
        title = _normalize_text(row.get("title") or "")
        support = _first_int(row.get("support_count"))
        if title and title.lower() not in hint.lower():
            rendered = f"{title}: {hint}"
        else:
            rendered = hint
        if support > 1 and rendered:
            rendered = f"{rendered} (đã lặp lại {support} lần)"
        lines.append(f"- {rendered}")
        count += 1
        if count >= limit:
            break

    return "\n".join(lines).strip() if count else ""


_FALLBACK_MARKERS = (
    "chưa có tool",
    "không có tool",
    "chua co tool",
    "khong co tool",
    "chưa tóm tắt được",
    "chua tom tat duoc",
    "chưa đọc được",
    "chua doc duoc",
    "không tìm thấy",
    "khong tim thay",
    "xin lỗi",
    "xin loi",
)

_PREFERENCE_CUES = (
    "dài hơn",
    "dai hon",
    "ngắn hơn",
    "ngan hon",
    "kỹ hơn",
    "ky hon",
    "chi tiết hơn",
    "chi tiet hon",
    "dễ nhìn hơn",
    "de nhin hon",
    "dễ đọc hơn",
    "de doc hon",
    "gọn hơn",
    "gon hon",
    "ít chữ hơn",
    "it chu hon",
)

_DEEP_DOCUMENT_CUES = (
    "phân tích sâu",
    "phan tich sau",
    "phân tích kỹ",
    "phan tich ky",
    "tóm tắt kỹ",
    "tom tat ky",
    "tóm tắt chi tiết",
    "tom tat chi tiet",
    "chi tiết hơn",
    "chi tiet hon",
    "nhiều trang",
    "nhieu trang",
    "nhiều page",
    "nhieu page",
    "bóc tách",
    "boc tach",
)

_FOLLOWUP_CUES = (
    "trong file",
    "trong tài liệu",
    "trong tai lieu",
    "file này",
    "file nay",
    "tài liệu này",
    "tai lieu nay",
    "nội dung này",
    "noi dung nay",
    "ý gì",
    "y gi",
    "dùng thế nào",
    "dung the nao",
    "là gì",
    "la gi",
    "giải thích",
    "giai thich",
)


def classify_learning_issue(
    *,
    request_text: str,
    final_text: str,
    tools_called: Iterable[str] | None = None,
    trace: dict[str, Any] | None = None,
    source: str = "",
    scope: str = "",
    topic: str = "",
    warnings: Iterable[str] | None = None,
) -> tuple[str, int, str]:
    request = _normalize_text(request_text).lower()
    final = _normalize_text(final_text).lower()
    tool_names = [str(tool).strip() for tool in (tools_called or []) if str(tool).strip()]
    warning_set = {str(item).strip() for item in (warnings or []) if str(item).strip()}
    trace_payload = _extract_llm_trace(trace or {})

    if any(marker in final for marker in _FALLBACK_MARKERS):
        return ("fallback", 2, "Phản hồi đang dùng câu fallback hoặc báo thiếu khả năng.")

    if "vision_fallback_local" in warning_set or "vision_unavailable" in warning_set:
        return ("vision_fallback", 1, "Ảnh đang phải rơi về fallback local.")

    if any(cue in request for cue in _PREFERENCE_CUES):
        return ("preference_signal", 0, "Người dùng đang đưa tín hiệu về độ dài/format mong muốn.")

    if scope == "document" and any(cue in request for cue in _DEEP_DOCUMENT_CUES):
        return ("deep_document_request", 0, "Người dùng muốn tóm tắt hoặc phân tích tài liệu sâu hơn.")

    if scope == "document" and any(cue in request for cue in _FOLLOWUP_CUES):
        return ("document_followup", 0, "Người dùng đang hỏi tiếp tài liệu vừa xử lý.")

    if source == "media" and tool_names and tool_names[0].startswith("document_") and any(cue in request for cue in _FOLLOWUP_CUES):
        return ("document_followup", 0, "Người dùng đang hỏi tiếp tài liệu vừa xử lý.")

    if trace_payload.get("cache_hit") is True or _first_int(trace_payload.get("cached_tokens")) > 0:
        return ("cache_hit", 0, "Lượt này có prompt cache hit.")

    return ("ok", 0, "")


@dataclass(frozen=True)
class LearningInsight:
    scope: str
    topic: str
    title: str
    prompt_hint: str
    memory_hint: str
    confidence: float
    support_count: int
    examples: list[dict[str, Any]]
    source_digest: str


class LearningRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def setup(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_learning_events (
                      id BIGSERIAL PRIMARY KEY,
                      chat_id TEXT NOT NULL,
                      request_id TEXT NOT NULL,
                      thread_id TEXT NOT NULL DEFAULT '',
                      source TEXT NOT NULL DEFAULT 'chat',
                      scope TEXT NOT NULL DEFAULT 'general',
                      topic TEXT NOT NULL DEFAULT '',
                      user_text TEXT NOT NULL DEFAULT '',
                      final_text TEXT NOT NULL DEFAULT '',
                      tools_called TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                      issue_type TEXT NOT NULL DEFAULT '',
                      severity INTEGER NOT NULL DEFAULT 0,
                      model TEXT NOT NULL DEFAULT '',
                      prompt_cache_key TEXT NOT NULL DEFAULT '',
                      cache_hit BOOLEAN NOT NULL DEFAULT FALSE,
                      cached_tokens INTEGER NOT NULL DEFAULT 0,
                      prompt_tokens INTEGER NOT NULL DEFAULT 0,
                      completion_tokens INTEGER NOT NULL DEFAULT 0,
                      total_tokens INTEGER NOT NULL DEFAULT 0,
                      trace JSONB NOT NULL DEFAULT '{}'::JSONB,
                      metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
                      notes TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_learning_insights (
                      id BIGSERIAL PRIMARY KEY,
                      scope TEXT NOT NULL DEFAULT 'general',
                      topic TEXT NOT NULL DEFAULT '',
                      title TEXT NOT NULL DEFAULT '',
                      prompt_hint TEXT NOT NULL DEFAULT '',
                      memory_hint TEXT NOT NULL DEFAULT '',
                      support_count INTEGER NOT NULL DEFAULT 0,
                      confidence DOUBLE PRECISION NOT NULL DEFAULT 0,
                      examples JSONB NOT NULL DEFAULT '[]'::JSONB,
                      source_digest TEXT NOT NULL UNIQUE,
                      is_active BOOLEAN NOT NULL DEFAULT TRUE,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_events_chat_created ON mia_learning_events (chat_id, created_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_events_scope_created ON mia_learning_events (scope, created_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_events_issue ON mia_learning_events (issue_type, created_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_insights_scope_active ON mia_learning_insights (scope, is_active, confidence DESC, support_count DESC, updated_at DESC);"
                )
                cur.execute(
                    "ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0;"
                )
                cur.execute(
                    "ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;"
                )
                cur.execute(
                    "ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS promoted_at TIMESTAMPTZ;"
                )
                cur.execute(
                    "ALTER TABLE mia_learning_insights ADD COLUMN IF NOT EXISTS decay_score DOUBLE PRECISION NOT NULL DEFAULT 0;"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_insights_usage ON mia_learning_insights (is_active, usage_count DESC, last_used_at DESC);"
                )
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_learning_feedbacks (
                      id BIGSERIAL PRIMARY KEY,
                      chat_id TEXT NOT NULL,
                      request_id TEXT NOT NULL,
                      thread_id TEXT NOT NULL DEFAULT '',
                      source TEXT NOT NULL DEFAULT 'chat',
                      scope TEXT NOT NULL DEFAULT 'general',
                      topic TEXT NOT NULL DEFAULT '',
                      verdict TEXT NOT NULL DEFAULT '',
                      rating INTEGER NOT NULL DEFAULT 0,
                      comment TEXT NOT NULL DEFAULT '',
                      correction_text TEXT NOT NULL DEFAULT '',
                      current_text TEXT NOT NULL DEFAULT '',
                      trace JSONB NOT NULL DEFAULT '{}'::JSONB,
                      metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_feedbacks_chat_created ON mia_learning_feedbacks (chat_id, created_at DESC);"
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_learning_feedbacks_scope_created ON mia_learning_feedbacks (scope, created_at DESC);"
                )
            conn.commit()

    def record_event(
        self,
        *,
        chat_id: str,
        request_id: str,
        source: str,
        scope: str,
        topic: str = "",
        thread_id: str = "",
        user_text: str = "",
        final_text: str = "",
        tools_called: Iterable[str] | None = None,
        trace: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        issue_type: str = "",
        severity: int = 0,
        notes: str = "",
    ) -> dict[str, Any]:
        llm_trace = _extract_llm_trace(trace or {})
        cached_tokens = _first_int(llm_trace.get("cached_tokens"))
        prompt_tokens = _first_int(llm_trace.get("prompt_tokens"))
        completion_tokens = _first_int(llm_trace.get("completion_tokens"))
        total_tokens = _first_int(llm_trace.get("total_tokens"))
        if not total_tokens and prompt_tokens and completion_tokens:
            total_tokens = prompt_tokens + completion_tokens
        model = _normalize_text(llm_trace.get("model") or "")
        prompt_cache_key = _normalize_text(llm_trace.get("prompt_cache_key") or "")
        cache_hit = bool(llm_trace.get("cache_hit")) or cached_tokens > 0
        clean_tools = _normalize_list(list(tools_called or []))

        payload = {
            "chat_id": str(chat_id or "").strip(),
            "request_id": str(request_id or "").strip(),
            "thread_id": str(thread_id or "").strip(),
            "source": _normalize_text(source) or "chat",
            "scope": _normalize_text(scope) or "general",
            "topic": _normalize_text(topic),
            "user_text": _normalize_text(user_text),
            "final_text": _normalize_text(final_text),
            "tools_called": clean_tools,
            "issue_type": _normalize_text(issue_type),
            "severity": max(0, int(severity or 0)),
            "model": model,
            "prompt_cache_key": prompt_cache_key,
            "cache_hit": cache_hit,
            "cached_tokens": cached_tokens,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "trace": trace or {},
            "metadata": metadata or {},
            "notes": _normalize_text(notes),
        }

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_learning_events (
                      chat_id, request_id, thread_id, source, scope, topic, user_text, final_text,
                      tools_called, issue_type, severity, model, prompt_cache_key, cache_hit,
                      cached_tokens, prompt_tokens, completion_tokens, total_tokens, trace, metadata, notes, created_at
                    )
                    VALUES (
                      %(chat_id)s, %(request_id)s, %(thread_id)s, %(source)s, %(scope)s, %(topic)s,
                      %(user_text)s, %(final_text)s, %(tools_called)s, %(issue_type)s, %(severity)s,
                      %(model)s, %(prompt_cache_key)s, %(cache_hit)s, %(cached_tokens)s, %(prompt_tokens)s,
                      %(completion_tokens)s, %(total_tokens)s, %(trace)s::jsonb, %(metadata)s::jsonb,
                      %(notes)s, now()
                    )
                    RETURNING id, chat_id, request_id, scope, topic, issue_type, created_at;
                    """,
                    {
                        **payload,
                        "trace": json.dumps(payload["trace"]),
                        "metadata": json.dumps(payload["metadata"]),
                    },
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row or payload)

    def record_feedback(
        self,
        *,
        chat_id: str,
        request_id: str,
        source: str = "chat",
        scope: str = "general",
        topic: str = "",
        verdict: str = "",
        rating: int = 0,
        comment: str = "",
        correction_text: str = "",
        current_text: str = "",
        thread_id: str = "",
        trace: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_verdict = _normalize_verdict(verdict)
        clean_comment = _normalize_text(comment)
        clean_correction_text = _normalize_text(correction_text)
        clean_current_text = _normalize_text(current_text)
        clean_scope = _normalize_text(scope) or "general"
        clean_topic = _normalize_text(topic)
        clean_source = _normalize_text(source) or "chat"
        payload = {
            "chat_id": str(chat_id or "").strip(),
            "request_id": str(request_id or "").strip(),
            "thread_id": str(thread_id or "").strip(),
            "source": clean_source,
            "scope": clean_scope,
            "topic": clean_topic,
            "verdict": clean_verdict,
            "rating": int(rating or 0),
            "comment": clean_comment,
            "correction_text": clean_correction_text,
            "current_text": clean_current_text,
            "trace": trace or {},
            "metadata": metadata or {},
        }

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_learning_feedbacks (
                      chat_id, request_id, thread_id, source, scope, topic, verdict, rating,
                      comment, correction_text, current_text, trace, metadata, created_at
                    )
                    VALUES (
                      %(chat_id)s, %(request_id)s, %(thread_id)s, %(source)s, %(scope)s, %(topic)s,
                      %(verdict)s, %(rating)s, %(comment)s, %(correction_text)s, %(current_text)s,
                      %(trace)s::jsonb, %(metadata)s::jsonb, now()
                    )
                    RETURNING id, chat_id, request_id, scope, topic, verdict, rating, created_at;
                    """,
                    {
                        **payload,
                        "trace": json.dumps(payload["trace"]),
                        "metadata": json.dumps(payload["metadata"]),
                    },
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row or payload)

    def recent_events(
        self,
        *,
        scope: str = "",
        topic: str = "",
        source: str = "",
        chat_id: str = "",
        limit: int = 200,
        days: int = 14,
    ) -> list[dict[str, Any]]:
        clauses = ["created_at >= now() - (%s || ' days')::interval"]
        params: list[Any] = [max(1, int(days or 1))]
        if scope.strip():
            clauses.append("scope = %s")
            params.append(scope.strip())
        if topic.strip():
            clauses.append("topic = %s")
            params.append(topic.strip())
        if source.strip():
            clauses.append("source = %s")
            params.append(source.strip())
        if chat_id.strip():
            clauses.append("chat_id = %s")
            params.append(chat_id.strip())
        params.append(max(1, int(limit or 1)))
        sql = f"""
        SELECT
          id, chat_id, request_id, thread_id, source, scope, topic, user_text, final_text,
          tools_called, issue_type, severity, model, prompt_cache_key, cache_hit, cached_tokens,
          prompt_tokens, completion_tokens, total_tokens, trace, metadata, notes, created_at
        FROM mia_learning_events
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC, id DESC
        LIMIT %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def recent_feedback(
        self,
        *,
        scope: str = "",
        topic: str = "",
        source: str = "",
        chat_id: str = "",
        limit: int = 200,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        clauses = ["created_at >= now() - (%s || ' days')::interval"]
        params: list[Any] = [max(1, int(days or 1))]
        if scope.strip():
            clauses.append("scope = %s")
            params.append(scope.strip())
        if topic.strip():
            clauses.append("topic = %s")
            params.append(topic.strip())
        if source.strip():
            clauses.append("source = %s")
            params.append(source.strip())
        if chat_id.strip():
            clauses.append("chat_id = %s")
            params.append(chat_id.strip())
        params.append(max(1, int(limit or 1)))
        sql = f"""
        SELECT
          id, chat_id, request_id, thread_id, source, scope, topic, verdict, rating,
          comment, correction_text, current_text, trace, metadata, created_at
        FROM mia_learning_feedbacks
        WHERE {" AND ".join(clauses)}
        ORDER BY created_at DESC, id DESC
        LIMIT %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def list_active_insights(
        self,
        *,
        scopes: Iterable[str] | None = None,
        topics: Iterable[str] | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        scope_values = [str(scope).strip() for scope in (scopes or []) if str(scope).strip()]
        topic_values = [str(topic).strip() for topic in (topics or []) if str(topic).strip()]

        clauses = ["is_active = TRUE"]
        params: list[Any] = []
        if scope_values:
            clauses.append("scope = ANY(%s)")
            params.append(scope_values)
        if topic_values:
            clauses.append("topic = ANY(%s)")
            params.append(topic_values)
        params.append(max(1, int(limit or 1)))
        sql = f"""
        SELECT
          id, scope, topic, title, prompt_hint, memory_hint, support_count, confidence,
          usage_count, last_used_at, promoted_at, decay_score,
          examples, source_digest, is_active, created_at, updated_at
        FROM mia_learning_insights
        WHERE {" AND ".join(clauses)}
        ORDER BY
          (confidence + LEAST(0.12 * support_count, 0.48) - LEAST(EXTRACT(EPOCH FROM (now() - COALESCE(last_used_at, updated_at, created_at))) / 86400.0, 90) * 0.003) DESC,
          support_count DESC,
          usage_count DESC,
          updated_at DESC
        LIMIT %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())

    def touch_insights(self, insight_ids: Iterable[int]) -> None:
        ids = [int(item) for item in insight_ids if str(item).strip()]
        if not ids:
            return
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_learning_insights
                    SET usage_count = usage_count + 1,
                        last_used_at = now(),
                        decay_score = GREATEST(decay_score - 0.05, 0),
                        updated_at = now()
                    WHERE id = ANY(%s);
                    """,
                    (ids,),
                )
            conn.commit()

    def decay_stale_insights(self, *, max_age_days: int = 45, min_support: int = 1) -> int:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_learning_insights
                    SET is_active = FALSE,
                        decay_score = decay_score + 1,
                        updated_at = now()
                    WHERE is_active = TRUE
                      AND support_count <= %s
                      AND COALESCE(last_used_at, promoted_at, updated_at, created_at) < now() - (%s || ' days')::interval
                    RETURNING id;
                    """,
                    (max(0, int(min_support)), max(1, int(max_age_days))),
                )
                rows = cur.fetchall()
            conn.commit()
        return len(rows or [])

    def upsert_insight(
        self,
        *,
        scope: str,
        topic: str,
        title: str,
        prompt_hint: str,
        memory_hint: str = "",
        support_count: int = 1,
        confidence: float = 0.65,
        examples: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        clean_scope = _normalize_text(scope) or "general"
        clean_topic = _normalize_text(topic)
        clean_title = _normalize_text(title)
        clean_prompt_hint = _normalize_text(prompt_hint)
        clean_memory_hint = _normalize_text(memory_hint)
        clean_examples = list(examples or [])
        source_digest = _hash_digest(clean_scope, clean_topic, clean_prompt_hint, clean_memory_hint)

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_learning_insights (
                      scope, topic, title, prompt_hint, memory_hint, support_count, confidence,
                      usage_count, last_used_at, promoted_at, decay_score,
                      examples, source_digest, is_active, created_at, updated_at
                    )
                    VALUES (
                      %s, %s, %s, %s, %s, %s, %s, 0, NULL, now(), 0.0, %s::jsonb, %s, TRUE, now(), now()
                    )
                    ON CONFLICT (source_digest)
                    DO UPDATE SET
                      scope = EXCLUDED.scope,
                      topic = EXCLUDED.topic,
                      title = EXCLUDED.title,
                      prompt_hint = EXCLUDED.prompt_hint,
                      memory_hint = EXCLUDED.memory_hint,
                      support_count = mia_learning_insights.support_count + EXCLUDED.support_count,
                      confidence = GREATEST(mia_learning_insights.confidence, EXCLUDED.confidence),
                      decay_score = LEAST(mia_learning_insights.decay_score, EXCLUDED.decay_score),
                      usage_count = GREATEST(mia_learning_insights.usage_count, EXCLUDED.usage_count),
                      examples = CASE
                        WHEN jsonb_array_length(mia_learning_insights.examples) >= jsonb_array_length(EXCLUDED.examples)
                        THEN mia_learning_insights.examples
                        ELSE EXCLUDED.examples
                      END,
                      is_active = TRUE,
                      promoted_at = COALESCE(mia_learning_insights.promoted_at, now()),
                      updated_at = now()
                    RETURNING id, scope, topic, title, prompt_hint, memory_hint, support_count, confidence,
                              usage_count, last_used_at, promoted_at, decay_score, examples, source_digest;
                    """,
                    (
                        clean_scope,
                        clean_topic,
                        clean_title,
                        clean_prompt_hint,
                        clean_memory_hint,
                        max(1, int(support_count or 1)),
                        float(confidence or 0.0),
                        json.dumps(clean_examples),
                        source_digest,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row or {})

    def record_feedback_as_insight(
        self,
        *,
        chat_id: str,
        request_id: str,
        source: str,
        scope: str,
        topic: str,
        verdict: str,
        rating: int,
        comment: str,
        correction_text: str,
        current_text: str,
        trace: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        allow_single_support: bool = False,
    ) -> dict[str, Any] | None:
        feedback_row = self.record_feedback(
            chat_id=chat_id,
            request_id=request_id,
            source=source,
            scope=scope,
            topic=topic,
            verdict=verdict,
            rating=rating,
            comment=comment,
            correction_text=correction_text,
            current_text=current_text,
            trace=trace,
            metadata=metadata,
        )
        candidate = _feedback_style_payload(verdict, comment, current_text, correction_text)
        if candidate is None:
            return {"feedback": feedback_row, "insight": None}
        feedback_signals = [
            verdict,
            comment,
            correction_text,
            current_text,
        ]
        has_feedback = any(_normalize_text(value) for value in feedback_signals)
        should_promote, _ = should_promote_candidate(
            support_count=1,
            confidence=float(candidate.get("confidence") or 0.0),
            has_feedback=has_feedback,
            allow_single_support=allow_single_support,
        )
        if not should_promote:
            return {"feedback": feedback_row, "insight": None}
        insight = self.upsert_insight(**candidate)
        return {"feedback": feedback_row, "insight": insight}

    def runtime_summary(self, *, days: int = 7, source: str = "n8n_tool") -> dict[str, Any]:
        events = self.recent_events(source=source, limit=5000, days=max(1, int(days or 1)))
        total = len(events)
        success_count = sum(1 for row in events if str(row.get("issue_type") or "") == "tool_success")
        fail_count = sum(1 for row in events if str(row.get("issue_type") or "") == "tool_fail")
        approval_count = sum(1 for row in events if str(row.get("issue_type") or "") == "approval_required")
        other_count = max(0, total - success_count - fail_count - approval_count)
        success_events = [row for row in events if str(row.get("issue_type") or "") == "tool_success"]
        latency_values = []
        by_gateway: dict[str, dict[str, Any]] = {}

        for row in events:
            metadata = row.get("metadata") or {}
            if not isinstance(metadata, dict):
                metadata = {}
            gateway_name = str(metadata.get("gateway_name") or row.get("topic") or row.get("scope") or "").strip() or "unknown"
            bucket = by_gateway.setdefault(
                gateway_name,
                {
                    "gateway_name": gateway_name,
                    "total": 0,
                    "success": 0,
                    "fail": 0,
                    "approval_required": 0,
                    "latency_total_ms": 0.0,
                },
            )
            bucket["total"] += 1
            issue_type = str(row.get("issue_type") or "")
            if issue_type == "tool_success":
                bucket["success"] += 1
            elif issue_type == "tool_fail":
                bucket["fail"] += 1
            elif issue_type == "approval_required":
                bucket["approval_required"] += 1
            latency_ms = metadata.get("latency_ms")
            try:
                latency_float = float(latency_ms)
            except (TypeError, ValueError):
                latency_float = 0.0
            if latency_float > 0:
                bucket["latency_total_ms"] += latency_float
                latency_values.append(latency_float)

        gateway_rows = []
        for bucket in sorted(by_gateway.values(), key=lambda item: (item["total"], item["success"], item["gateway_name"]), reverse=True):
            total_bucket = int(bucket["total"] or 0)
            success_bucket = int(bucket["success"] or 0)
            fail_bucket = int(bucket["fail"] or 0)
            approval_bucket = int(bucket["approval_required"] or 0)
            gateway_rows.append(
                {
                    "gateway_name": bucket["gateway_name"],
                    "total": total_bucket,
                    "success": success_bucket,
                    "fail": fail_bucket,
                    "approval_required": approval_bucket,
                    "success_rate": round((success_bucket / total_bucket) * 100, 1) if total_bucket else 0.0,
                    "fail_rate": round((fail_bucket / total_bucket) * 100, 1) if total_bucket else 0.0,
                    "approval_rate": round((approval_bucket / total_bucket) * 100, 1) if total_bucket else 0.0,
                    "avg_latency_ms": round(bucket["latency_total_ms"] / total_bucket, 1) if total_bucket and bucket["latency_total_ms"] else 0.0,
                }
            )

        summary = {
            "days": max(1, int(days or 1)),
            "source": source,
            "total": total,
            "success": success_count,
            "fail": fail_count,
            "approval_required": approval_count,
            "other": other_count,
            "success_rate": round((success_count / total) * 100, 1) if total else 0.0,
            "fail_rate": round((fail_count / total) * 100, 1) if total else 0.0,
            "approval_rate": round((approval_count / total) * 100, 1) if total else 0.0,
            "avg_latency_ms": round(sum(latency_values) / len(latency_values), 1) if latency_values else 0.0,
            "by_gateway": gateway_rows[:10],
        }
        if success_events:
            summary["last_success"] = {
                "gateway_name": str((success_events[0].get("metadata") or {}).get("gateway_name") or success_events[0].get("topic") or ""),
                "created_at": success_events[0].get("created_at"),
            }
        return summary
