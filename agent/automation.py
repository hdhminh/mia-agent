from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from croniter import croniter

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class AutomationRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def setup(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_automations (
                      id BIGSERIAL PRIMARY KEY,
                      chat_id TEXT NOT NULL,
                      user_id TEXT NOT NULL,
                      name TEXT NOT NULL,
                      schedule TEXT NOT NULL,
                      skill_name TEXT NOT NULL,
                      input_text TEXT NOT NULL DEFAULT '',
                      enabled BOOLEAN NOT NULL DEFAULT TRUE,
                      next_run_at TIMESTAMPTZ,
                      last_run_at TIMESTAMPTZ,
                      lease_until TIMESTAMPTZ,
                      last_error TEXT NOT NULL DEFAULT '',
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    );
                    """
                )
                cur.execute("ALTER TABLE mia_automations ADD COLUMN IF NOT EXISTS lease_until TIMESTAMPTZ;")
                cur.execute("ALTER TABLE mia_automations ADD COLUMN IF NOT EXISTS last_error TEXT NOT NULL DEFAULT '';")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_mia_automations_due ON mia_automations (enabled, next_run_at);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_mia_automations_owner ON mia_automations (user_id, updated_at DESC);")
            conn.commit()

    def create(self, *, chat_id: str, user_id: str, name: str, schedule: str, skill_name: str, input_text: str = "", next_run_at: str | None = None) -> dict[str, Any]:
        resolved_next_run = next_run_at or compute_next_run(schedule).isoformat()
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_automations (chat_id, user_id, name, schedule, skill_name, input_text, next_run_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::timestamptz)
                    RETURNING *;
                    """,
                    (chat_id, user_id, name, schedule, skill_name, input_text, resolved_next_run),
                )
                row = cur.fetchone() or {}
            conn.commit()
        return dict(row)

    def list(self, *, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM mia_automations WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s", (user_id, max(1, min(limit, 100))))
                return [dict(row) for row in cur.fetchall()]

    def get(self, *, automation_id: int, user_id: str) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM mia_automations WHERE id = %s AND user_id = %s", (automation_id, user_id))
                row = cur.fetchone()
        return dict(row) if row else None

    def set_enabled(self, *, automation_id: int, user_id: str, enabled: bool) -> dict[str, Any] | None:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("UPDATE mia_automations SET enabled=%s, updated_at=now() WHERE id=%s AND user_id=%s RETURNING *", (enabled, automation_id, user_id))
                row = cur.fetchone()
            conn.commit()
        return dict(row) if row else None

    def delete(self, *, automation_id: int, user_id: str) -> bool:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM mia_automations WHERE id=%s AND user_id=%s RETURNING id", (automation_id, user_id))
                deleted = cur.fetchone() is not None
            conn.commit()
        return deleted

    def touch_run(self, *, automation_id: int) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE mia_automations SET last_run_at=now(), updated_at=now() WHERE id=%s", (automation_id,))
            conn.commit()

    def claim_due(self, *, limit: int = 10) -> list[dict[str, Any]]:
        """Atomically lease due automations so multiple workers cannot execute them twice."""
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    WITH due AS (
                      SELECT id
                      FROM mia_automations
                      WHERE enabled = TRUE
                        AND next_run_at IS NOT NULL
                        AND next_run_at <= now()
                        AND (lease_until IS NULL OR lease_until <= now())
                      ORDER BY next_run_at
                      FOR UPDATE SKIP LOCKED
                      LIMIT %s
                    )
                    UPDATE mia_automations AS automation
                    SET lease_until = now() + INTERVAL '5 minutes', updated_at = now()
                    FROM due
                    WHERE automation.id = due.id
                    RETURNING automation.*;
                    """,
                    (max(1, min(limit, 50)),),
                )
                rows = [dict(row) for row in cur.fetchall()]
            conn.commit()
        return rows

    def finish_run(self, *, automation_id: int, schedule: str, error_text: str = "") -> None:
        next_run = compute_next_run(schedule)
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_automations
                    SET last_run_at = now(), next_run_at = %s, lease_until = NULL,
                        last_error = %s, updated_at = now()
                    WHERE id = %s
                    """,
                    (next_run, str(error_text or "")[:2000], automation_id),
                )
            conn.commit()

    def summary(self) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT count(*) AS total,
                           count(*) FILTER (WHERE enabled) AS enabled,
                           count(*) FILTER (WHERE enabled AND next_run_at <= now()) AS due,
                           count(*) FILTER (WHERE last_error <> '') AS failed
                    FROM mia_automations;
                    """
                )
                return dict(cur.fetchone() or {})


def compute_next_run(schedule: str, *, after: datetime | None = None) -> datetime:
    expression = str(schedule or "").strip()
    if not expression or not croniter.is_valid(expression):
        raise ValueError("Automation schedule must be a valid cron expression (for example: '0 8 * * *').")
    base = after or datetime.now(timezone.utc)
    return croniter(expression, base).get_next(datetime)
