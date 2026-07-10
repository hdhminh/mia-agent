from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
    ) -> list[dict[str, Any]]:
        clean_query = _normalize_text(query)
        if not clean_query:
            return []

        query_embedding = self._embed([clean_query], input_type="query")[0]
        vector_text = _vector_literal(query_embedding)
        search_limit = max(limit * 4, 8)
        like_query = f"%{clean_query}%"

        sql = """
        WITH semantic AS (
          SELECT
            i.id AS item_id,
            c.chunk_text,
            c.chunk_index,
            i.memory_type,
            i.title,
            i.tags,
            i.importance,
            i.confidence,
            i.source,
            i.expires_at,
            i.created_at,
            1 - (c.embedding <=> CAST(%s AS vector)) AS semantic_score,
            (
              CASE WHEN c.chunk_text ILIKE %s THEN 0.12 ELSE 0 END +
              CASE WHEN i.title ILIKE %s THEN 0.08 ELSE 0 END +
              CASE WHEN array_to_string(i.tags, ' ') ILIKE %s THEN 0.05 ELSE 0 END
            ) AS keyword_bonus
          FROM mia_memory_chunks c
          JOIN mia_memory_items i ON i.id = c.item_id
          WHERE c.chat_id = %s
            AND i.is_active = TRUE
            AND (i.expires_at IS NULL OR i.expires_at > now())
            AND (%s = '' OR i.memory_type = %s)
          ORDER BY c.embedding <=> CAST(%s AS vector)
          LIMIT %s
        )
        SELECT
          item_id,
          chunk_text,
          chunk_index,
          memory_type,
          title,
          tags,
          importance,
          confidence,
          source,
          expires_at,
          created_at,
          semantic_score,
          keyword_bonus,
          semantic_score + keyword_bonus
            + LEAST(importance, 5) * 0.015
            + LEAST(GREATEST(confidence, 0), 1) * 0.05
            + 0.04 / (1 + EXTRACT(EPOCH FROM (now() - created_at)) / 86400 / 30)
            AS final_score
        FROM semantic
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
                        like_query,
                        like_query,
                        like_query,
                        chat_id,
                        memory_type,
                        memory_type,
                        vector_text,
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
    ) -> list[dict[str, Any]]:
        sql = """
        SELECT
          id,
          chat_id,
          memory_type,
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
        WHERE chat_id = %s
          AND is_active = TRUE
          AND (expires_at IS NULL OR expires_at > now())
        ORDER BY updated_at DESC, importance DESC, created_at DESC
        LIMIT %s;
        """

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql, (chat_id, max(1, limit)))
                return list(cur.fetchall())

    def write(
        self,
        *,
        chat_id: str,
        content: str,
        memory_type: str = "general",
        title: str = "",
        tags: list[str] | None = None,
        importance: int = 3,
        source_text: str = "",
        confidence: float = 0.75,
        source: str = "mia_langchain_core",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_content = _normalize_text(content)
        if not normalized_content:
            raise ValueError("Memory content is empty.")

        clean_tags = [tag.strip() for tag in (tags or []) if str(tag).strip()]
        chunk_texts = _chunk_text(normalized_content)
        embeddings = self._embed(chunk_texts, input_type="passage")
        fingerprint = hashlib.sha256(
            f"{chat_id}|{memory_type}|{normalized_content}".encode("utf-8")
        ).hexdigest()[:32]

        metadata = {
            "memory_type": memory_type,
            "title": title,
            "tags": clean_tags,
            "importance": importance,
            "source": source,
            "confidence": max(0.0, min(float(confidence), 1.0)),
            "expires_at": expires_at,
            "source_text": source_text or normalized_content,
        }

        upsert_sql = """
        INSERT INTO mia_memory_items (
          chat_id, fingerprint, memory_type, title, content, source_text, tags,
          importance, confidence, source, expires_at, metadata, is_active, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::timestamptz, %s::jsonb, TRUE, now(), now())
        ON CONFLICT (fingerprint)
        DO UPDATE SET
          memory_type = EXCLUDED.memory_type,
          title = EXCLUDED.title,
          content = EXCLUDED.content,
          source_text = EXCLUDED.source_text,
          tags = EXCLUDED.tags,
          importance = EXCLUDED.importance,
          confidence = EXCLUDED.confidence,
          source = EXCLUDED.source,
          expires_at = EXCLUDED.expires_at,
          metadata = EXCLUDED.metadata,
          is_active = TRUE,
          updated_at = now()
        RETURNING id, chat_id, memory_type, title, tags, importance;
        """

        insert_chunk_sql = """
        INSERT INTO mia_memory_chunks (
          item_id, chat_id, chunk_index, chunk_text, embedding, metadata, created_at
        )
        VALUES (%s, %s, %s, %s, CAST(%s AS vector), %s::jsonb, now());
        """

        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    upsert_sql,
                    (
                        chat_id,
                        fingerprint,
                        memory_type,
                        title,
                        normalized_content,
                        source_text or normalized_content,
                        clean_tags,
                        importance,
                        metadata["confidence"],
                        source,
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
            "memory_type": item["memory_type"],
            "title": item["title"],
            "tags": item["tags"] or [],
            "importance": item["importance"],
            "confidence": metadata["confidence"],
            "source": source,
            "expires_at": expires_at,
            "chunk_count": len(chunk_texts),
            "content": normalized_content,
        }
