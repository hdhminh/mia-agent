from __future__ import annotations

import re


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
    return cleaned.strip("-") or "default"


def build_prompt_cache_key(*, namespace: str, scope: str, version: str) -> str:
    return ":".join(
        [
            _slugify(namespace),
            _slugify(scope),
            _slugify(version),
        ]
    )
