from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

from agent.service import MiaAgentService
from agent.approval import ApprovalRepository
from agent.config import Settings
from agent.error_envelope import ErrorSource, build_exception_envelope
from agent.i18n import t
from agent.learning.repository import LearningRepository
from agent.memory.repository import MemoryRepository
from agent.models import MiaChatRequest, MiaChatResponse, MiaFeedbackRequest, MiaFeedbackResponse
from agent.execution_client import N8nToolGatewayClient
from agent.skills.media_service.routes import router as media_router
from agent.skills.media_service.service import MediaService
from agent.skills.web_service.routes import router as web_router
from agent.skills.web_service.service import WebService


BASE_DIR = Path(__file__).resolve().parent.parent
if (BASE_DIR / "infra" / "sql" / "memory_schema.sql").exists():
    MEMORY_SCHEMA_PATH = BASE_DIR / "infra" / "sql" / "memory_schema.sql"
else:
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
    learning_repo = LearningRepository(pool=pool)
    learning_repo.setup()
    approval_repo = ApprovalRepository(pool=pool)
    approval_repo.setup()

    checkpointer_cm = PostgresSaver.from_conn_string(settings.postgres_uri)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()

    tool_gateway = N8nToolGatewayClient(
        url=settings.tool_gateway_url,
        token=settings.tool_gateway_token,
        timeout_seconds=settings.request_timeout_seconds,
        learning_repo=learning_repo,
        approval_repo=approval_repo,
    )
    media_service = MediaService(settings=settings, learning_repo=learning_repo)
    web_service = WebService(settings=settings, memory_repo=memory_repo)

    app.state.settings = settings
    app.state.pool = pool
    app.state.memory_repo = memory_repo
    app.state.learning_repo = learning_repo
    app.state.approval_repo = approval_repo
    app.state.checkpointer_cm = checkpointer_cm
    app.state.checkpointer = checkpointer
    app.state.media_service = media_service
    app.state.web_service = web_service
    app.state.agent_service = MiaAgentService(
        settings=settings,
        memory_repo=memory_repo,
        learning_repo=learning_repo,
        tool_gateway=tool_gateway,
        checkpointer=checkpointer,
    )

    try:
        yield
    finally:
        checkpointer_cm.__exit__(None, None, None)
        pool.close()


app = FastAPI(title="Mia LangChain Core", lifespan=lifespan)
app.include_router(media_router)
app.include_router(web_router)


@app.middleware("http")
async def require_core_api_token(request: Request, call_next):
    path = request.url.path or "/"
    protected = path == "/mia/chat" or path.startswith("/mia/media/")
    protected = protected or path.startswith("/mia/ops/")
    public = path in {"/health", "/mia/media/health"}
    if not protected or public:
        return await call_next(request)

    settings: Settings | None = getattr(request.app.state, "settings", None)
    expected_token = (settings.core_api_token if settings else "").strip()
    if not expected_token:
        return JSONResponse(status_code=503, content={"detail": "Mia core auth is not configured."})

    auth_header = str(request.headers.get("authorization") or "").strip()
    bearer_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
    provided_token = str(request.headers.get("x-mia-core-token") or bearer_token).strip()
    if provided_token != expected_token:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized mia-core token."})

    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "mia-core"}


@app.post("/mia/chat", response_model=MiaChatResponse)
def mia_chat(request: MiaChatRequest) -> MiaChatResponse:
    service: MiaAgentService = app.state.agent_service
    return service.chat(request)


@app.post("/mia/feedback", response_model=MiaFeedbackResponse)
def mia_feedback(request: MiaFeedbackRequest) -> MiaFeedbackResponse:
    learning_repo: LearningRepository = app.state.learning_repo
    try:
        promoted = learning_repo.record_feedback_as_insight(
            chat_id=request.chat_id,
            request_id=request.request_id,
            source=request.source,
            scope=request.scope,
            topic=request.topic,
            verdict=request.verdict,
            rating=request.rating,
            comment=request.comment,
            correction_text=request.correction_text,
            current_text=request.current_text,
            trace=request.trace,
            metadata=request.metadata,
            allow_single_support=True,
        )
        feedback = promoted.get("feedback") or {}
        insight = promoted.get("insight") or {}
        feedback_id = int(feedback.get("id")) if feedback.get("id") is not None else None
        insight_id = int(insight.get("id")) if insight.get("id") is not None else None
        return MiaFeedbackResponse(
            ok=True,
            feedback_id=feedback_id,
            insight_id=insight_id,
            message=t("api.feedback_recorded", default="Feedback đã được ghi nhận."),
        )
    except Exception as exc:
        envelope = build_exception_envelope(
            exc,
            code="feedback_record_failed",
            category="internal",
            severity="error",
            user_message=t("api.feedback_record_failed", default="Mia chưa ghi nhận được feedback này. Bạn thử lại sau nhé."),
            retryable=False,
            source=ErrorSource(
                layer="api",
                component="app",
                operation="mia_feedback",
            ),
            request_id=request.request_id,
            thread_id=request.thread_id,
            chat_id=request.chat_id,
        )
        return JSONResponse(
            status_code=400,
            content=MiaFeedbackResponse(
                ok=False,
                message=envelope.display_text(),
                error=envelope,
            ).model_dump(mode="json"),
        )


@app.get("/mia/ops/metrics")
def mia_ops_metrics(days: int = 7) -> dict[str, object]:
    learning_repo: LearningRepository = app.state.learning_repo
    approval_repo: ApprovalRepository = app.state.approval_repo
    return {
        "tool_gateway": learning_repo.runtime_summary(days=max(1, int(days or 7))),
        "pending_actions": approval_repo.pending_summary(days=max(1, int(days or 7))),
    }
