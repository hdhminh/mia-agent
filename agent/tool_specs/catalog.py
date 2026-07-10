from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


CATALOG_PATH = Path(__file__).with_name("catalog.yaml")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    action: str
    domain: str
    description: str
    risk: str = "read"
    approval: str = "never"
    idempotent: bool = False
    timeout_seconds: int = 30
    executor: str = "n8n"
    workflow_key: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ToolSpec":
        return cls(
            name=str(value.get("name") or "").strip(),
            action=str(value.get("action") or "").strip(),
            domain=str(value.get("domain") or "general").strip(),
            description=str(value.get("description") or "").strip(),
            risk=str(value.get("risk") or "read").strip(),
            approval=str(value.get("approval") or "never").strip(),
            idempotent=bool(value.get("idempotent")),
            timeout_seconds=max(1, int(value.get("timeout_seconds") or 30)),
            executor=str(value.get("executor") or "n8n").strip(),
            workflow_key=str(value.get("workflow_key") or value.get("action") or "").strip(),
            tags=tuple(str(item).strip() for item in value.get("tags", []) if str(item).strip()),
        )


class ToolCatalog:
    def __init__(self, specs: Iterable[ToolSpec]) -> None:
        self.specs = tuple(specs)
        self.by_name = {spec.name: spec for spec in self.specs}
        self.by_action = {spec.action: spec for spec in self.specs}
        if len(self.by_name) != len(self.specs):
            raise ValueError("ToolSpec catalog contains duplicate Python tool names.")

    @classmethod
    def load(cls, path: Path = CATALOG_PATH) -> "ToolCatalog":
        # JSON is valid YAML 1.2; using JSON keeps the runtime dependency-free.
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload.get("tools") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("ToolSpec catalog must contain a tools list.")
        specs = [ToolSpec.from_dict(row) for row in rows if isinstance(row, dict)]
        invalid = [spec for spec in specs if not spec.name or not spec.action]
        if invalid:
            raise ValueError("Every ToolSpec requires name and action.")
        return cls(specs)

    def domain(self, domain: str) -> list[ToolSpec]:
        return [spec for spec in self.specs if spec.domain == domain]

    def write_actions(self) -> set[str]:
        return {spec.action for spec in self.specs if spec.risk in {"write", "external_write", "destructive"}}
