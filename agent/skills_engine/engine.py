from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


SKILL_CATALOG_PATH = Path(__file__).with_name("skills.yaml")


@dataclass(frozen=True)
class SkillSpec:
    name: str
    description: str
    triggers: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    steps: tuple[str, ...]
    approval_points: tuple[str, ...]
    success_criteria: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SkillSpec":
        return cls(
            name=str(value.get("name") or "").strip(),
            description=str(value.get("description") or "").strip(),
            triggers=tuple(str(item).strip() for item in value.get("triggers", []) if str(item).strip()),
            required_capabilities=tuple(str(item).strip() for item in value.get("required_capabilities", []) if str(item).strip()),
            steps=tuple(str(item).strip() for item in value.get("steps", []) if str(item).strip()),
            approval_points=tuple(str(item).strip() for item in value.get("approval_points", []) if str(item).strip()),
            success_criteria=tuple(str(item).strip() for item in value.get("success_criteria", []) if str(item).strip()),
        )


class SkillStateRepository:
    def __init__(self, pool: ConnectionPool) -> None:
        self.pool = pool

    def setup(self) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS mia_skill_runs (
                      id BIGSERIAL PRIMARY KEY,
                      skill_name TEXT NOT NULL,
                      request_id TEXT NOT NULL UNIQUE,
                      chat_id TEXT NOT NULL,
                      user_id TEXT NOT NULL,
                      status TEXT NOT NULL DEFAULT 'running',
                      current_step INTEGER NOT NULL DEFAULT 0,
                      completed_steps JSONB NOT NULL DEFAULT '[]'::jsonb,
                      state JSONB NOT NULL DEFAULT '{}'::jsonb,
                      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                      completed_at TIMESTAMPTZ
                    );
                    """
                )
                cur.execute("CREATE INDEX IF NOT EXISTS idx_mia_skill_runs_owner ON mia_skill_runs (user_id, updated_at DESC);")
            conn.commit()

    def start(self, *, spec: SkillSpec, request_id: str, chat_id: str, user_id: str) -> dict[str, Any]:
        with self.pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO mia_skill_runs (skill_name, request_id, chat_id, user_id, status, state)
                    VALUES (%s, %s, %s, %s, 'running', %s::jsonb)
                    ON CONFLICT (request_id) DO UPDATE SET updated_at = now()
                    RETURNING *;
                    """,
                    (spec.name, request_id, chat_id, user_id, json.dumps({"steps": spec.steps}, ensure_ascii=False)),
                )
                row = cur.fetchone() or {}
            conn.commit()
        return dict(row)

    def finish(self, *, request_id: str, status: str, state: dict[str, Any] | None = None) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_skill_runs
                    SET status = %s, state = state || %s::jsonb, updated_at = now(),
                        completed_at = CASE WHEN %s IN ('completed', 'failed', 'cancelled') THEN now() ELSE completed_at END
                    WHERE request_id = %s
                    """,
                    (status, json.dumps(state or {}, ensure_ascii=False), status, request_id),
                )
            conn.commit()

    def pause(self, *, request_id: str, state: dict[str, Any] | None = None) -> None:
        self.finish(request_id=request_id, status="waiting_approval", state=state)

    def finish_latest(self, *, chat_id: str, user_id: str, status: str, state: dict[str, Any] | None = None) -> None:
        with self.pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE mia_skill_runs
                    SET status = %s, state = state || %s::jsonb, updated_at = now(), completed_at = now()
                    WHERE id = (
                      SELECT id FROM mia_skill_runs
                      WHERE chat_id = %s AND user_id = %s AND status IN ('running', 'waiting_approval')
                      ORDER BY updated_at DESC LIMIT 1
                    );
                    """,
                    (status, json.dumps(state or {}, ensure_ascii=False), chat_id, user_id),
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
                           count(DISTINCT skill_name) AS skills
                    FROM mia_skill_runs
                    WHERE created_at >= now() - (%s * INTERVAL '1 day');
                    """,
                    (max(1, int(days)),),
                )
                return dict(cur.fetchone() or {})


class SkillEngine:
    def __init__(self, *, repository: SkillStateRepository, specs: list[SkillSpec]) -> None:
        self.repository = repository
        self.specs = specs

    @classmethod
    def load(cls, *, repository: SkillStateRepository, path: Path = SKILL_CATALOG_PATH) -> "SkillEngine":
        payload = json.loads(path.read_text(encoding="utf-8"))
        specs = [SkillSpec.from_dict(row) for row in payload.get("skills", []) if isinstance(row, dict)]
        return cls(repository=repository, specs=specs)

    def select(self, query: str) -> SkillSpec | None:
        normalized = " ".join(str(query or "").lower().split())
        best: tuple[int, SkillSpec] | None = None
        for spec in self.specs:
            score = 0
            for trigger in spec.triggers:
                trigger_text = " ".join(trigger.lower().split())
                if trigger_text and trigger_text in normalized:
                    score = max(score, len(trigger_text.split()) + 3)
                else:
                    score += len(set(re.findall(r"\w+", trigger_text)) & set(re.findall(r"\w+", normalized)))
            if score and (best is None or score > best[0]):
                best = (score, spec)
        return best[1] if best and best[0] >= 3 else None

    def start_guidance(self, *, query: str, request_id: str, chat_id: str, user_id: str) -> tuple[str, str]:
        spec = self.select(query)
        if spec is None:
            return "", ""
        self.repository.start(spec=spec, request_id=request_id, chat_id=chat_id, user_id=user_id)
        lines = [
            f"Execute reusable skill: {spec.name}.",
            f"Goal: {spec.description}",
            "Required capabilities: " + ", ".join(spec.required_capabilities),
            "Steps:",
        ]
        lines.extend(f"{index + 1}. {step}" for index, step in enumerate(spec.steps))
        if spec.approval_points:
            lines.append("Pause for explicit approval before: " + ", ".join(spec.approval_points))
        lines.append("Success criteria: " + "; ".join(spec.success_criteria))
        return spec.name, "\n".join(lines)
