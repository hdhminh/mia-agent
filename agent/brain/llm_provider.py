from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from agent.config import Settings
from agent.brain.prompt_cache import build_prompt_cache_key

PRIMARY_PROVIDER_OPENROUTER = "openrouter"
PRIMARY_PROVIDER_DEEPSEEK_DIRECT = "deepseek_direct"


def normalize_llm_provider(value: str) -> str:
    normalized = str(value or "").strip().lower().replace("-", "_")
    if normalized in {"deepseek", "deepseek_direct"}:
        return PRIMARY_PROVIDER_DEEPSEEK_DIRECT
    if normalized == "openrouter":
        return PRIMARY_PROVIDER_OPENROUTER
    return normalized


def _cache_key(settings: Settings, *, scope: str, provider: str) -> str | None:
    if not settings.prompt_cache_enabled:
        return None
    return build_prompt_cache_key(
        namespace=settings.prompt_cache_namespace,
        scope=f"{provider}:{scope}",
        version=settings.prompt_cache_version,
    )


def build_chat_model(
    settings: Settings,
    *,
    scope: str,
    provider: str | None = None,
    model_override: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cache_enabled: bool = True,
) -> ChatOpenAI:
    chosen_provider = normalize_llm_provider(provider or settings.primary_llm_provider)
    cache_key = _cache_key(settings, scope=scope, provider=chosen_provider) if cache_enabled else None

    kwargs: dict[str, Any]
    if chosen_provider == PRIMARY_PROVIDER_OPENROUTER:
        kwargs = dict(
            model=model_override or settings.model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=settings.temperature if temperature is None else temperature,
            max_tokens=settings.max_tokens if max_tokens is None else max_tokens,
            default_headers={
                "HTTP-Referer": settings.openrouter_referer,
                "X-Title": settings.openrouter_title,
            },
        )
        if cache_key:
            kwargs["model_kwargs"] = {"prompt_cache_key": cache_key}
        return ChatOpenAI(**kwargs)

    if chosen_provider == PRIMARY_PROVIDER_DEEPSEEK_DIRECT:
        kwargs = dict(
            model=model_override or settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=settings.temperature if temperature is None else temperature,
            max_tokens=settings.max_tokens if max_tokens is None else max_tokens,
        )
        return ChatOpenAI(**kwargs)

    raise RuntimeError(f"Unsupported LLM provider: {chosen_provider}")


def build_primary_and_fallback_models(
    settings: Settings,
    *,
    scope: str,
    provider: str | None = None,
    model_override: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    cache_enabled: bool = True,
) -> tuple[ChatOpenAI, ChatOpenAI | None]:
    chosen_provider = normalize_llm_provider(provider or settings.primary_llm_provider)
    primary = build_chat_model(
        settings,
        scope=scope,
        provider=chosen_provider,
        model_override=model_override,
        temperature=temperature,
        max_tokens=max_tokens,
        cache_enabled=cache_enabled,
    )

    fallback: ChatOpenAI | None = None
    if chosen_provider == PRIMARY_PROVIDER_DEEPSEEK_DIRECT and settings.openrouter_api_key:
        fallback = build_chat_model(
            settings,
            scope=scope,
            provider=PRIMARY_PROVIDER_OPENROUTER,
            model_override=settings.model,
            temperature=temperature,
            max_tokens=max_tokens,
            cache_enabled=cache_enabled,
        )
    return primary, fallback
