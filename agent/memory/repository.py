from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

import httpx
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"


def _chunk_text(text: str, max_length: int = 350, overlap: int = 60) -> list[str]:
    compact = _normalize_text(text)
    if not compact:
        return []
    if len(compact) <= max_length:
        return [compact]

    segments = [segment for segment in compact.replace("\n", " ").split(". ") if segment]
    chunks: list[str] = []
    current = ""

    for segment in segments:
        candidate = segment if not current else f"{current}. {segment}"
        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current.strip())

        carry = current[-overlap:].strip() if current else ""
        current = f"{carry} {segment}".strip() if carry else segment

    if current:
        chunks.append(current.strip())

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= max_length:
            final_chunks.append(chunk)
            continue
        step = max_length - overlap
        for start in range(0, len(chunk), step):
            final_chunks.append(chunk[start : start + max_length].strip())

    return [chunk for chunk in final_chunks if chunk]


def _rrf(rank: int, *, k: int = 60) -> float:
    return 1.0 / (k + max(1, rank))


def _normalize_memory_kind(value: str) -> str:
    clean = _normalize_text(value).lower()
    if clean in {"semantic", "episodic", "procedural"}:
        return clean
    return "semantic"


def _proposal_fingerprint(owner_id: str, content: str, memory_type: str) -> str:
    normalized = _normalize_text(content).lower()
    return hashlib.sha256(f"{owner_id}|{memory_type}|{normalized}".encode("utf-8")).hexdigest()[:32]


SECRET_PATTERNS = (
    re.compile(r"\b(api[_ -]?key|token|secret|password|pass|mật khẩu|mat khau)\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9_-]{32,}\b"),
)


def looks_like_durable_memory(text: str) -> bool:
    normalized = _normalize_text(text).lower()
    if len(normalized) < 18:
        return False
    if any(pattern.search(normalized) for pattern in SECRET_PATTERNS):
        return False
    cues = (
        "hãy nhớ",
        "hay nho",
        "nhớ là",
        "nho la",
        "mình thích",
        "minh thich",
        "mình muốn",
        "minh muon",
        "ưu tiên",
        "uu tien",
        "từ giờ",
        "tu gio",
        "luôn",
        "luon",
        "không bao giờ",
        "khong bao gio",
        "default",
        "mặc định",
        "mac dinh",
        "project",
        "workspace",
    )
    return any(cue in normalized for cue in cues)


def build_memory_context(rows: list[dict[str, Any]], *, token_budget: int = 600) -> str:
    if not rows:
        return ""
    max_chars = max(300, token_budget * 4)
    lines = ["Memory context liên quan đã được retrieve tự động. Chỉ dùng nếu phù hợp với yêu cầu hiện tại:"]
    used = len(lines[0])
    for index, row in enumerate(rows, start=1):
        memory_type = str(row.get("memory_type") or "general").strip()
        memory_kind = str(row.get("memory_kind") or "semantic").strip()
        title = str(row.get("title") or "").strip()
        content = str(row.get("chunk_text") or row.get("content") or "").strip()
        if not content:
            continue
        snippet = content[:320].rstrip()
        if len(content) > 320:
            snippet += "..."
        line = f"{index}. [{memory_kind}/{memory_type}]"
        if title:
            line += f" {title}:"
        line = f"{line} {snippet}".strip()
        if used + len(line) + 1 > max_chars:
            break
        lines.append(line)
        used += len(line) + 1
    return "\n".join(lines) if len(lines) > 1 else ""


class MemoryRepository:
    def __init__(
        self,
        pool: ConnectionPool,
        embedder_url: str,
        timeout_seconds: float,
        schema_path: Path,
    ) -> None:
        self.pool = pool
        self.embedder_url = embedder_url
        self.timeout_seconds = timeout_seconds
        self.schema_path = schema_path

    def setup(self) -> None:
        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()

    def _embed(self, texts: list[str], input_type: str) -> list[list[float]]:
        if not texts:
            return []

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                self.embedder_url,
                json={"texts": texts, "input_type": input_type},
            )
            response.raise_for_status()
            data = response.json()

        embeddings = data.get("embeddings") or []
        if len(embeddings) != len(texts):
            raise RuntimeError("Embedding service returned an unexpected number of vectors.")
        return embeddings

    def search(
        self,
        *,
        chat_id: str,
        query: str,
        limit: int = 5,
        threshold: float = 0.45,
        memory_type: str = "",
        owner_id: str = "",
        memory_kind: str = "",
    ) -> list[dict[str, Any]]:
        clean_query = _normalize_text(query)
        if not clean_query:
            return []

        query_embedding = self._embed([clean_query], input_type="query")[0]
        vector_text = _vector_literal(query_embedding)
        search_limit = max(limit * 8, 16)
        like_query = f"%{clean_query}%"
        owner_filter = _normalize_text(owner_id or chat_id)
        kind_filter = _normalize_text(memory_kind).lower()

        sql = """
        WITH semantic AS (
          SELECT
            i.id AS item_id,
            c.chunk_text,
            c.chunk_index,
            i.memory_type,
            i.memory_kind,
            i.title,
            i.tags,
            i.importance,
            i.confidence,
            i.source,
            i.expires_at,
            i.owner_id,
            i.created_at,
            1 - (c.embedding <=> CAST(%s AS vector)) AS semantic_score,
            row_number() OVER (ORDER BY c.embedding <=> CAST(%s AS vector)) AS semantic_rank,
            NULL::BIGINT AS lexical_rank,
            (
              CASE WHEN c.chunk_text ILIKE %s THEN 0.12 ELSE 0 END +
              CASE WHEN i.title ILIKE %s THEN 0.08 ELSE 0 END +
              CASE WHEN array_to_string(i.tags, ' ') ILIKE %s THEN 0.05 ELSE 0 END
            ) AS keyword_bonus
          FROM mia_memory_chunks c
          JOIN mia_memory_items i ON i.id = c.item_id
          WHERE i.owner_id = %s
            AND i.is_active = TRUE
            AND i.status = 'active'
            AND i.superseded_by IS NULL
            AND (i.expires_at IS NULL OR i.expires_at > now())
            AND (i.valid_to IS NULL OR i.valid_to > now())
            AND (%s = '' OR i.memory_type = %s)
            AND (%s = '' OR i.memory_kind = %s)
          ORDER BY c.embedding <=> CAST(%s AS vector)
          LIMIT %s
        ),
        lexical AS (
          SELECT
            i.id AS item_id,
            c.chunk_text,
            c.chunk_index,
            i.memory_type,
            i.memory_kind,
            i.title,
            i.tags,
            i.importance,
            i.confidence,
            i.source,
            i.expires_at,
            i.owner_id,
            i.created_at,
            0::double precision AS semantic_score,
            NULL::BIGINT AS semantic_rank,
            row_number() OVER (
              ORDER BY
                CASE WHEN c.chunk_text ILIKE %s THEN 3 ELSE 0 END +
                CASE WHEN i.title ILIKE %s THEN 2 ELSE 0 END +
                CASE WHEN array_to_string(i.tags, ' ') ILIKE %s THEN 1 ELSE 0 END DESC,
                word_similarity(%s, c.chunk_text) DESC,
                i.importance DESC,
                i.updated_at DESC
            ) AS lexical_rank,
            (
              CASE WHEN c.chunk_text ILIKE %s THEN 0.18 ELSE 0 END +
              CASE WHEN i.title ILIKE %s THEN 0.14 ELSE 0 END +
              CASE WHEN array_to_string(i.tags, ' ') ILIKE %s THEN 0.08 ELSE 0 END +
              LEAST(word_similarity(%s, c.chunk_text), 1) * 0.10
            ) AS keyword_bonus
          FROM mia_memory_chunks c
          JOIN mia_memory_items i ON i.id = c.item_id
          WHERE i.owner_id = %s
            AND i.is_active = TRUE
            AND i.status = 'active'
            AND i.superseded_by IS NULL
            AND (i.expires_at IS NULL OR i.expires_at > now())
            AND (i.valid_to IS NULL OR i.valid_to > now())
            AND (%s = '' OR i.memory_type = %s)
            AND (%s = '' OR i.memory_kind = %s)
            AND (
              c.chunk_text ILIKE %s OR
              i.title ILIKE %s OR
              array_to_string(i.tags, ' ') ILIKE %s OR
              word_similarity(%s, c.chunk_text) > 0.2
            )
          LIMIT %s
        ),
        merged AS (
          SELECT * FROM semantic
          UNION ALL
          SELECT * FROM lexical
        ),
        ranked AS (
          SELECT
            item_id,
            chunk_text,
            chunk_index,
            memory_type,
            memory_kind,
            title,
            tags,
            importance,
            confidence,
            source,
            expires_at,
            owner_id,
            created_at,
            max(semantic_score) AS semantic_score,
            max(keyword_bonus) AS keyword_bonus,
            min(semantic_rank) AS semantic_rank,
            min(lexical_rank) AS lexical_rank
          FROM merged
          GROUP BY item_id, chunk_text, chunk_index, memory_type, memory_kind, title, tags,
                   importance, confidence, source, expires_at, owner_id, created_at
        )
        SELECT
          item_id,
          chunk_text,
          chunk_index,
          memory_type,
          memory_kind,
          title,
          tags,
          importance,
          confidence,
          source,
          expires_at,
          owner_id,
          created_at,
          semantic_score,
          keyword_bonus,
          COALESCE(1.0 / (60 + semantic_rank), 0)
            + COALESCE(1.0 / (60 + lexical_rank), 0)
            + semantic_score * 0.25
            + keyword_bonus
            + LEAST(importance, 5) * 0.015
            + LEAST(GREATEST(confidence, 0), 1) * 0.05
            + 0.04 / (1 + EXTRACT(EPOCH FROM (now() - created_at)) / 86400 / 30)
            AS final_score
        FROM ranked
        WHERE semantic_score >= %s OR keyword_bonus > 0
        ORDER BY final_score DESC, importance DESC, created_at DESC
        LIMIT %s;
        """

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    sql,
                    (
                        vector_text,
                        vector_text,
                        like_query,
                        like_query,
                        like_query,
                        owner_filter,
                        memory_type,
                        memory_type,
                        kind_filter,
                        kind_filter,
                        vector_text,
                        search_limit,
                        like_query,
                        like_query,
                        like_query,
                        clean_query,
                        like_query,
                        like_query,
                        like_query,
                        clean_query,
                        owner_filter,
                        memory_type,
                        memory_type,
                        kind_filter,
                        kind_filter,
                        like_query,
                        like_query,
                        like_query,
                        clean_query,
                        search_limit,
                        threshold,
                        limit,
                    ),
                )
                rows = list(cur.fetchall())
                item_ids = sorted({int(row["item_id"]) for row in rows if row.get("item_id") is not None})
                if item_ids:
                    cur.execute(
                        "UPDATE mia_memory_items SET last_used_at = now() WHERE id = ANY(%s);",
                        (item_ids,),
                    )
                    conn.commit()
                return rows

    def recent(
        self,
        *,
        chat_id: str,
        limit: int = 5,
        owner_id: str = "",
    ) -> list[dict[str, Any]]:
        owner_filter = _normalize_text(owner_id or chat_id)
        sql = """
        SELECT
          id,
          chat_id,
          owner_id,
          thread_id,
          memory_type,
          memory_kind,
          title,
          content,
          tags,
          importance,
          confidence,
          source,
          last_used_at,
          expires_at,
          created_at,
          updated_at
        FROM mia_memory_items
        WHERE owner_id = %s
          AND is_active = TRUE
          AND status = 'active'
          AND superseded_by IS NULL
          AND (expires_at IS NULL OR expires_at > now())
          AND (valid_to IS NULL OR valid_to > now())
        ORDER BY updated_at DESC, importance DESC, created_at DESC
        LIMIT %s;
        """

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (owner_filter, max(1, limit)))
                return list(cur.fetchall())

    def write(
        self,
        *,
        chat_id: str,
        content: str,
        memory_type: str = "general",
        memory_kind: str = "semantic",
        title: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        source_text: str = "",
        confidence: float = 0.75,
        source: str = "mia_langchain_core",
        expires_at: str | None = None,
        owner_id: str = "",
        thread_id: str = "",
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        normalized_content = _normalize_text(content)
        if not normalized_content:
            raise ValueError("Memory content is empty.")

        clean_tags = [tag.strip() for tag in (tags or []) if str(tag).strip()]
        clean_kind = _normalize_memory_kind(memory_kind)
        owner_filter = _normalize_text(owner_id or chat_id)
        clean_thread_id = _normalize_text(thread_id)
        chunk_texts = _chunk_text(normalized_content)
        embeddings = self._embed(chunk_texts, input_type="passage")
        fingerprint = hashlib.sha256(
            f"{owner_filter}|{memory_type}|{clean_kind}|{normalized_content}".encode("utf-8")
        ).hexdigest()[:32]

        metadata = {
            "memory_type": memory_type,
            "memory_kind": clean_kind,
            "title": title,
            "tags": clean_tags,
            "importance": importance,
            "source": source,
            "confidence": max(0.0, min(float(confidence), 1.0)),
            "expires_at": expires_at,
            "source_text": source_text or normalized_content,
        }
        clean_evidence = evidence or []

        upsert_sql = """
        INSERT INTO mia_memory_items (
          chat_id, owner_id, thread_id, fingerprint, memory_type, memory_kind, status,
          title, content, source_text, tags, importance, confidence, source, evidence,
          expires_at, metadata, is_active, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'active', %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::timestamptz, %s::jsonb, TRUE, now(), now())
        ON CONFLICT (fingerprint)
        DO UPDATE SET
          chat_id = EXCLUDED.chat_id,
          owner_id = EXCLUDED.owner_id,
          thread_id = EXCLUDED.thread_id,
          memory_type = EXCLUDED.memory_type,
          memory_kind = EXCLUDED.memory_kind,
          status = 'active',
          title = EXCLUDED.title,
          content = EXCLUDED.content,
          source_text = EXCLUDED.source_text,
          tags = EXCLUDED.tags,
          importance = EXCLUDED.importance,
          confidence = EXCLUDED.confidence,
          source = EXCLUDED.source,
          evidence = EXCLUDED.evidence,
          expires_at = EXCLUDED.expires_at,
          metadata = EXCLUDED.metadata,
          is_active = TRUE,
          updated_at = now()
        RETURNING id, chat_id, owner_id, thread_id, memory_type, memory_kind, title, tags, importance;
        """

        insert_chunk_sql = """
        INSERT INTO mia_memory_chunks (
          item_id, chat_id, owner_id, chunk_index, chunk_text, embedding, metadata, created_at
        )
        VALUES (%s, %s, %s, %s, %s, CAST(%s AS vector), %s::jsonb, now());
        """

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    upsert_sql,
                    (
                        chat_id,
                        owner_filter,
                        clean_thread_id,
                        fingerprint,
                        memory_type,
                        clean_kind,
                        title,
                        normalized_content,
                        source_text or normalized_content,
                        clean_tags,
                        importance,
                        metadata["confidence"],
                        source,
                        json.dumps(clean_evidence),
                        expires_at,
                        json.dumps(metadata),
                    ),
                )
                item = cur.fetchone()
                if item is None:
                    raise RuntimeError("Failed to upsert memory item.")

                cur.execute(
                    "DELETE FROM mia_memory_chunks WHERE item_id = %s;",
                    (item["id"],),
                )

                for index, (chunk, vector) in enumerate(zip(chunk_texts, embeddings, strict=True)):
                    cur.execute(
                        insert_chunk_sql,
                            (
                                item["id"],
                                chat_id,
                                owner_filter,
                                index,
                                chunk,
                                _vector_literal(vector),
                            json.dumps(metadata),
                        ),
                    )

            conn.commit()

        return {
            "id": item["id"],
            "chat_id": item["chat_id"],
            "owner_id": item["owner_id"],
            "thread_id": item["thread_id"],
            "memory_type": item["memory_type"],
            "memory_kind": item["memory_kind"],
            "title": item["title"],
            "tags": item["tags"] or [],
            "importance": item["importance"],
            "confidence": metadata["confidence"],
            "source": source,
            "expires_at": expires_at,
            "chunk_count": len(chunk_texts),
            "content": normalized_content,
        }

    def create_proposal(
        self,
        *,
        chat_id: str,
        owner_id: str,
        thread_id: str,
        request_id: str,
        content: str,
        memory_type: str = "general",
        memory_kind: str = "semantic",
        title: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        confidence: float = 0.65,
        source_text: str = "",
        evidence: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_content = _normalize_text(content)
        if not normalized_content:
            raise ValueError("Memory proposal content is empty.")
        if any(pattern.search(normalized_content) for pattern in SECRET_PATTERNS):
            raise ValueError("Memory proposal appears to contain a secret.")

        owner_filter = _normalize_text(owner_id or chat_id)
        clean_kind = _normalize_memory_kind(memory_kind)
        clean_tags = [tag.strip() for tag in (tags or []) if str(tag).strip()]
        fingerprint = _proposal_fingerprint(owner_filter, normalized_content, memory_type)
        metadata_payload = dict(metadata or {})
        metadata_payload["fingerprint"] = fingerprint

        sql = """
        INSERT INTO mia_memory_proposals (
          owner_id, chat_id, thread_id, request_id, memory_type, memory_kind, title,
          content, tags, importance, confidence, source_text, evidence, metadata, status,
          created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, 'pending', now(), now())
        RETURNING id, owner_id, chat_id, thread_id, request_id, memory_type, memory_kind,
                  title, content, tags, importance, confidence, status, expires_at, created_at;
        """
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, owner_id, chat_id, thread_id, request_id, memory_type, memory_kind,
                           title, content, tags, importance, confidence, status, expires_at, created_at
                    FROM mia_memory_proposals
                    WHERE owner_id = %s
                      AND status = 'pending'
                      AND metadata ->> 'fingerprint' = %s
                      AND expires_at > now()
                    ORDER BY created_at DESC
                    LIMIT 1;
                    """,
                    (owner_filter, fingerprint),
                )
                existing = cur.fetchone()
                if existing is not None:
                    return dict(existing)
                cur.execute(
                    sql,
                    (
                        owner_filter,
                        chat_id,
                        _normalize_text(thread_id),
                        _normalize_text(request_id),
                        memory_type or "general",
                        clean_kind,
                        _normalize_text(title),
                        normalized_content,
                        clean_tags,
                        max(1, min(int(importance), 5)),
                        max(0.0, min(float(confidence), 1.0)),
                        source_text or normalized_content,
                        json.dumps(evidence or []),
                        json.dumps(metadata_payload),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return dict(row or {})

    def list_pending_proposals(
        self,
        *,
        owner_id: str,
        chat_id: str = "",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        owner_filter = _normalize_text(owner_id or chat_id)
        sql = """
        SELECT id, owner_id, chat_id, thread_id, request_id, memory_type, memory_kind,
               title, content, tags, importance, confidence, status, expires_at, created_at
        FROM mia_memory_proposals
        WHERE owner_id = %s
          AND status = 'pending'
          AND expires_at > now()
          AND (%s = '' OR chat_id = %s)
        ORDER BY created_at DESC
        LIMIT %s;
        """
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (owner_filter, chat_id, chat_id, max(1, min(limit, 20))))
                return list(cur.fetchall())

    def accept_proposal(self, *, proposal_id: int, owner_id: str) -> dict[str, Any]:
        owner_filter = _normalize_text(owner_id)
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM mia_memory_proposals
                    WHERE id = %s
                      AND owner_id = %s
                      AND status = 'pending'
                      AND expires_at > now()
                    FOR UPDATE;
                    """,
                    (proposal_id, owner_filter),
                )
                proposal = cur.fetchone()
                if proposal is None:
                    raise ValueError("Memory proposal is not pending or does not belong to this owner.")
            conn.commit()

        saved = self.write(
            chat_id=str(proposal["chat_id"]),
            owner_id=str(proposal["owner_id"]),
            thread_id=str(proposal.get("thread_id") or ""),
            content=str(proposal["content"]),
            memory_type=str(proposal["memory_type"] or "general"),
            memory_kind=str(proposal["memory_kind"] or "semantic"),
            title=str(proposal.get("title") or ""),
            tags=list(proposal.get("tags") or []),
            importance=int(proposal.get("importance") or 3),
            source_text=str(proposal.get("source_text") or proposal["content"]),
            confidence=float(proposal.get("confidence") or 0.65),
            source="mia_memory_proposal",
            evidence=list(proposal.get("evidence") or []),
        )

        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_memory_proposals
                    SET status = 'accepted', accepted_item_id = %s, updated_at = now()
                    WHERE id = %s AND owner_id = %s;
                    """,
                    (saved["id"], proposal_id, owner_filter),
                )
            conn.commit()
        return saved

    def reject_proposal(self, *, proposal_id: int, owner_id: str, reason: str = "") -> None:
        owner_filter = _normalize_text(owner_id)
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_memory_proposals
                    SET status = 'rejected', rejection_reason = %s, updated_at = now()
                    WHERE id = %s AND owner_id = %s AND status = 'pending';
                    """,
                    (_normalize_text(reason), proposal_id, owner_filter),
                )
            conn.commit()
