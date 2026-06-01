from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    model: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_referer: str
    openrouter_title: str
    postgres_uri: str
    memory_embedder_url: str
    tool_gateway_url: str
    tool_gateway_token: str
    timezone: str
    temperature: float
    max_tokens: int
    recursion_limit: int
    history_max_tokens: int
    request_timeout_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model=os.getenv("MIA_MODEL", "openai/gpt-4.1-mini"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
            openrouter_base_url=os.getenv(
                "OPENROUTER_BASE_URL",
                "https://openrouter.ai/api/v1",
            ).strip(),
            openrouter_referer=os.getenv(
                "OPENROUTER_HTTP_REFERER",
                "https://n8n.huynhminh.com",
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
            timezone=os.getenv("MIA_TIMEZONE", "Asia/Ho_Chi_Minh").strip(),
            temperature=float(os.getenv("MIA_MODEL_TEMPERATURE", "0")),
            max_tokens=int(os.getenv("MIA_MODEL_MAX_TOKENS", "900")),
            recursion_limit=int(os.getenv("MIA_RECURSION_LIMIT", "7")),
            history_max_tokens=int(os.getenv("MIA_HISTORY_MAX_TOKENS", "1400")),
            request_timeout_seconds=float(os.getenv("MIA_REQUEST_TIMEOUT_SECONDS", "60")),
        )

    def validate(self) -> None:
        if not self.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for mia-core.")
