from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable

from agent.tool_specs import ToolCatalog


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[\wÀ-ỹ]+", str(value or "").lower()) if len(token) > 1}


class CapabilityBroker:
    def __init__(self, catalog: ToolCatalog) -> None:
        self.catalog = catalog

    @classmethod
    @lru_cache(maxsize=1)
    def default(cls) -> "CapabilityBroker":
        return cls(ToolCatalog.load())

    def select_tool_names(
        self,
        *,
        query: str,
        domain: str,
        available: Iterable[str],
        hint_tool: str = "",
        limit: int = 10,
    ) -> list[str]:
        available_names = list(dict.fromkeys(str(name) for name in available))
        query_tokens = _tokens(query)
        scored: list[tuple[int, str]] = []
        for name in available_names:
            spec = self.catalog.by_name.get(name)
            if spec is None:
                score = 0
            else:
                searchable = " ".join([spec.name, spec.action, spec.description, " ".join(spec.tags)])
                score = len(query_tokens & _tokens(searchable)) * 4
                if spec.domain == domain:
                    score += 3
                if name == hint_tool:
                    score += 100
            if name.startswith("memory_"):
                score += 2
            scored.append((score, name))
        scored.sort(key=lambda item: (-item[0], available_names.index(item[1])))
        core_memory_names = {"memory_search", "memory_recent", "memory_write"}
        proposal_memory_names = {
            "memory_pending_proposals",
            "memory_accept_proposal",
            "memory_reject_proposal",
        }
        proposal_tokens = {"memory", "memories", "proposal", "proposals", "duyet", "duyệt", "bo", "bỏ", "chap", "chấp", "nhan", "nhận"}
        pinned_memory = set(core_memory_names)
        if query_tokens & proposal_tokens:
            pinned_memory |= proposal_memory_names
        memory_names = [
            name
            for name in available_names
            if name in pinned_memory
        ]
        ranked = [name for _, name in scored if name not in memory_names]
        selected = memory_names + ranked[: max(1, limit - len(memory_names))]
        if hint_tool in available_names and hint_tool not in selected:
            selected[-1:] = [hint_tool]
        return selected
