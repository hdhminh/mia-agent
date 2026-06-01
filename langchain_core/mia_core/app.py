from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from mia_core.agent import MiaAgentService
from mia_core.config import Settings
from mia_core.memory import MemoryRepository
from mia_core.models import MiaChatRequest, MiaChatResponse
from mia_core.n8n_client import N8nToolGatewayClient


BASE_DIR = Path(__file__).resolve().parent.parent
MEMORY_SCHEMA_PATH = BASE_DIR / "sql" / "memory_schema.sql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    settings.validate()

    pool = ConnectionPool(conninfo=settings.postgres_uri, open=True)
    memory_repo = MemoryRepository(
        pool=pool,
        embedder_url=settings.memory_embedder_url,
        timeout_seconds=settings.request_timeout_seconds,
        schema_path=MEMORY_SCHEMA_PATH,
    )
    memory_repo.setup()

    checkpointer_cm = PostgresSaver.from_conn_string(settings.postgres_uri)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()

    tool_gateway = N8nToolGatewayClient(
        url=settings.tool_gateway_url,
        token=settings.tool_gateway_token,
        timeout_seconds=settings.request_timeout_seconds,
    )

    app.state.settings = settings
    app.state.pool = pool
    app.state.memory_repo = memory_repo
    app.state.checkpointer_cm = checkpointer_cm
    app.state.checkpointer = checkpointer
    app.state.agent_service = MiaAgentService(
        settings=settings,
        memory_repo=memory_repo,
        tool_gateway=tool_gateway,
        checkpointer=checkpointer,
    )

    try:
        yield
    finally:
        checkpointer_cm.__exit__(None, None, None)
        pool.close()


app = FastAPI(title="Mia LangChain Core", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mia-core"}


@app.post("/mia/chat", response_model=MiaChatResponse)
def mia_chat(request: MiaChatRequest) -> MiaChatResponse:
    service: MiaAgentService = app.state.agent_service
    return service.chat(request)
