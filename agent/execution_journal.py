from __future__ import annotations

import hashlib
import json
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def canonical_args_hash(args: dict[str, Any]) -> str:
    encoded = json.dumps(args or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_idempotency_key(*, user_id: str, request_id: str, tool_name: str, args: dict[str, Any]) -> str:
    material = "|".join(
        [str(user_id or "").strip(), str(request_id or "").strip(), str(tool_name or "").strip(), canonical_args_hash(args)]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class ExecutionJournalRepository:
    """Durable idempotency boundary for external write tools."""

    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def setup(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_execution_journal (
                      id BIGSERIAL PRIMARY KEY,
                      idempotency_key TEXT NOT NULL UNIQUE,
                      request_id TEXT NOT NULL,
                      chat_id TEXT NOT NULL,
                      user_id TEXT NOT NULL,
                      tool_name TEXT NOT NULL,
                      args_hash TEXT NOT NULL,
                      status TEXT NOT NULL DEFAULT 'running',
                      result JSONB NOT NULL DEFAULT '{}'::jsonb,
                      error_text TEXT NOT NULL DEFAULT '',
                      started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      completed_at TIMESTAMPTZ,
                      expires_at TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '30 days')
                    );
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_mia_execution_journal_owner ON mia_execution_journal (user_id, started_at DESC);"
                )
            conn.commit()

    def reserve(
        self,
        *,
        idempotency_key: str,
        request_id: str,
        chat_id: str,
        user_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> tuple[bool, dict[str, Any]]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_execution_journal (
                      idempotency_key, request_id, chat_id, user_id, tool_name, args_hash, status
                    ) VALUES (%s, %s, %s, %s, %s, %s, 'running')
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING *;
                    """,
                    (idempotency_key, request_id, chat_id, user_id, tool_name, canonical_args_hash(args)),
                )
                row = cur.fetchone()
                if row:
                    conn.commit()
                    return True, dict(row)
                cur.execute(
                    """
                    UPDATE mia_execution_journal
                    SET status = 'running', result = '{}'::jsonb, error_text = '',
                        started_at = now(), completed_at = NULL
                    WHERE idempotency_key = %s
                      AND (status = 'failed' OR (status = 'running' AND started_at < now() - INTERVAL '10 minutes'))
                    RETURNING *;
                    """,
                    (idempotency_key,),
                )
                reclaimed = cur.fetchone()
                if reclaimed:
                    conn.commit()
                    return True, dict(reclaimed)
                cur.execute("SELECT * FROM mia_execution_journal WHERE idempotency_key = %s", (idempotency_key,))
                existing = cur.fetchone() or {}
            conn.commit()
        return False, dict(existing)

    def finish(self, *, idempotency_key: str, status: str, result: dict[str, Any] | None = None, error_text: str = "") -> None:
        payload = json.dumps(result or {}, ensure_ascii=False, default=str)
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_execution_journal
                    SET status = %s, result = %s::jsonb, error_text = %s,
                        completed_at = now()
                    WHERE idempotency_key = %s
                    """,
                    (status, payload, str(error_text or ""), idempotency_key),
                )
            conn.commit()

    def summary(self, *, days: int = 7) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT count(*) AS total,
                           count(*) FILTER (WHERE status = 'completed') AS completed,
                           count(*) FILTER (WHERE status = 'failed') AS failed,
                           count(*) FILTER (WHERE status = 'running') AS running,
                           count(DISTINCT tool_name) AS tools
                    FROM mia_execution_journal
                    WHERE started_at >= now() - (%s * INTERVAL '1 day');
                    """,
                    (max(1, int(days)),),
                )
                return dict(cur.fetchone() or {})
