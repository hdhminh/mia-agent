from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    primary_llm_provider: str
    model: str
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_referer: str
    openrouter_title: str
    postgres_uri: str
    memory_embedder_url: str
    tool_gateway_url: str
    tool_gateway_token: str
    core_api_token: str
    timezone: str
    temperature: float
    max_tokens: int
    recursion_limit: int
    history_max_tokens: int
    request_timeout_seconds: float
    prompt_cache_enabled: bool
    prompt_cache_namespace: str
    prompt_cache_version: str
    groq_api_key: str
    groq_base_url: str
    groq_stt_model: str
    groq_tts_model: str
    groq_tts_voice: str
    groq_tts_format: str
    groq_vision_model: str
    ocr_languages: str
    evaluator_mode: str
    evaluator_max_retries: int
    owner_display_name: str
    locale: str

    @classmethod
    def from_env(cls) -> "Settings":
        primary_llm_provider = os.getenv("PRIMARY_LLM_PROVIDER", "openrouter").strip().lower()
        return cls(
            primary_llm_provider=primary_llm_provider,
            model=os.getenv("MIA_MODEL", "deepseek/deepseek-v4-flash").strip(),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            deepseek_model=os.getenv("MIA_DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ).strip(),
            openrouter_referer=os.getenv(
                "OPENROUTER_HTTP_REFERER",
                "https://n8n.example.com",
            ).strip(),
            openrouter_title=os.getenv("OPENROUTER_X_TITLE", "Mia LangChain Core").strip(),
            postgres_uri=os.getenv(
                "MIA_POSTGRES_URI",
                "postgresql://n8n:n8n_password@postgres:5432/vectordb?sslmode=disable",
            ).strip(),
            memory_embedder_url=os.getenv(
                "MIA_MEMORY_EMBEDDER_URL",
                "http://memory-embedder:8000/embed",
            ).strip(),
            tool_gateway_url=os.getenv(
                "MIA_TOOL_GATEWAY_URL",
                "http://n8n:5678/webhook/mia-tool",
            ).strip(),
            tool_gateway_token=os.getenv("MIA_TOOL_GATEWAY_TOKEN", "").strip(),
            core_api_token=os.getenv("MIA_CORE_API_TOKEN", "").strip(),
            timezone=os.getenv("MIA_TIMEZONE", "UTC").strip(),
            temperature=float(os.getenv("MIA_MODEL_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("MIA_MODEL_MAX_TOKENS", "900")),
            recursion_limit=int(os.getenv("MIA_RECURSION_LIMIT", "12")),
            history_max_tokens=int(os.getenv("MIA_HISTORY_MAX_TOKENS", "1400")),
            request_timeout_seconds=float(os.getenv("MIA_REQUEST_TIMEOUT_SECONDS", "60")),
            prompt_cache_enabled=_env_bool("MIA_PROMPT_CACHE_ENABLED", True),
            prompt_cache_namespace=os.getenv("MIA_PROMPT_CACHE_NAMESPACE", "mia").strip(),
            prompt_cache_version=os.getenv("MIA_PROMPT_CACHE_VERSION", "v1").strip(),
            groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
            groq_base_url=os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").strip(),
            groq_stt_model=os.getenv("MIA_GROQ_STT_MODEL", "whisper-large-v3-turbo").strip(),
            groq_tts_model=os.getenv("MIA_GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english").strip(),
            groq_tts_voice=os.getenv("MIA_GROQ_TTS_VOICE", "troy").strip(),
            groq_tts_format=os.getenv("MIA_GROQ_TTS_FORMAT", "wav").strip(),
            groq_vision_model=os.getenv(
                "MIA_GROQ_VISION_MODEL",
                "meta-llama/llama-4-scout-17b-16e-instruct",
            ).strip(),
            ocr_languages=os.getenv("MIA_OCR_LANGUAGES", "vie+eng").strip(),
            evaluator_mode=os.getenv("MIA_EVALUATOR_MODE", "hard").strip().lower(),
            evaluator_max_retries=int(os.getenv("MIA_EVALUATOR_MAX_RETRIES", "2")),
            owner_display_name=os.getenv("OWNER_DISPLAY_NAME", "User").strip(),
            locale=os.getenv("MIA_LOCALE", "en").strip().lower(),
        )

    def validate(self) -> None:
        if self.primary_llm_provider not in {"openrouter", "deepseek_direct"}:
            raise RuntimeError(
                "PRIMARY_LLM_PROVIDER must be either 'openrouter' or 'deepseek_direct'."
            )
        if self.primary_llm_provider == "openrouter":
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is required for mia-core.")
        elif self.primary_llm_provider == "deepseek_direct":
            if not self.deepseek_api_key:
                raise RuntimeError("DEEPSEEK_API_KEY is required for mia-core when PRIMARY_LLM_PROVIDER=deepseek_direct.")
            if not self.openrouter_api_key:
                raise RuntimeError("OPENROUTER_API_KEY is required as fallback when PRIMARY_LLM_PROVIDER=deepseek_direct.")
        if not self.tool_gateway_token:
            raise RuntimeError("MIA_TOOL_GATEWAY_TOKEN is required for mia-core.")
        if not self.core_api_token:
            raise RuntimeError("MIA_CORE_API_TOKEN is required for mia-core.")
        if self.evaluator_mode not in {"soft", "hard"}:
            raise RuntimeError("MIA_EVALUATOR_MODE must be either 'soft' or 'hard'.")
