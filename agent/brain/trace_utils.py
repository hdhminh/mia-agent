from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _as_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _first_int(*values: Any) -> int | None:
    for value in values:
        if value is None:
            continue
        if isinstance(value, bool):
            return int(value)
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def extract_prompt_cache_trace(
    source: Any,
    *,
    scope: str = "",
    model: str = "",
    prompt_cache_key: str = "",
) -> dict[str, Any]:
    response_metadata = _as_mapping(getattr(source, "response_metadata", None))
    usage_metadata = _as_mapping(getattr(source, "usage_metadata", None))
    additional_kwargs = _as_mapping(getattr(source, "additional_kwargs", None))

    if isinstance(source, Mapping):
        response_metadata = response_metadata or _as_mapping(source.get("response_metadata"))
        usage_metadata = usage_metadata or _as_mapping(source.get("usage_metadata"))
        additional_kwargs = additional_kwargs or _as_mapping(source.get("additional_kwargs"))

    usage_candidates = [
        response_metadata.get("token_usage"),
        response_metadata.get("usage"),
        response_metadata.get("usage_metadata"),
        usage_metadata,
        additional_kwargs.get("token_usage"),
        additional_kwargs.get("usage"),
        additional_kwargs.get("usage_metadata"),
    ]

    usage: dict[str, Any] = {}
    for candidate in usage_candidates:
        if isinstance(candidate, Mapping) and candidate:
            usage = dict(candidate)
            break

    prompt_details = {}
    for candidate in (
        usage.get("prompt_tokens_details"),
        usage.get("input_token_details"),
        response_metadata.get("prompt_tokens_details"),
        response_metadata.get("input_token_details"),
        additional_kwargs.get("prompt_tokens_details"),
        additional_kwargs.get("input_token_details"),
    ):
        if isinstance(candidate, Mapping) and candidate:
            prompt_details = dict(candidate)
            break

    cached_tokens = _first_int(
        prompt_details.get("cached_tokens"),
        prompt_details.get("cache_read"),
        prompt_details.get("cache_hit_tokens"),
        usage.get("cached_tokens"),
        usage.get("cache_hit_tokens"),
        response_metadata.get("cached_tokens"),
        response_metadata.get("cache_hit_tokens"),
        additional_kwargs.get("cached_tokens"),
        additional_kwargs.get("cache_hit_tokens"),
    )
    prompt_tokens = _first_int(
        usage.get("prompt_tokens"),
        usage.get("input_tokens"),
        response_metadata.get("prompt_tokens"),
        response_metadata.get("input_tokens"),
        additional_kwargs.get("prompt_tokens"),
        additional_kwargs.get("input_tokens"),
    )
    completion_tokens = _first_int(
        usage.get("completion_tokens"),
        usage.get("output_tokens"),
        response_metadata.get("completion_tokens"),
        response_metadata.get("output_tokens"),
        additional_kwargs.get("completion_tokens"),
        additional_kwargs.get("output_tokens"),
    )
    total_tokens = _first_int(
        usage.get("total_tokens"),
        response_metadata.get("total_tokens"),
        additional_kwargs.get("total_tokens"),
    )
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    cache_hit = bool(cached_tokens and cached_tokens > 0)
    return {
        "scope": scope,
        "model": model,
        "prompt_cache_key": prompt_cache_key,
        "cache_hit": cache_hit,
        "cached_tokens": cached_tokens or 0,
        "prompt_tokens": prompt_tokens or 0,
        "completion_tokens": completion_tokens or 0,
        "total_tokens": total_tokens or 0,
    }
