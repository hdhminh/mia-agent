from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import hmac
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
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
from agent.models import (
    MiaAutomationActionRequest,
    MiaAutomationRequest,
    MiaChatRequest,
    MiaChatResponse,
    MiaFeedbackRequest,
    MiaFeedbackResponse,
    MiaMCPCallRequest,
)
from agent.execution_client import N8nToolGatewayClient
from agent.execution_journal import ExecutionJournalRepository
from agent.skills.media_service.routes import router as media_router
from agent.skills.media_service.service import MediaService
from agent.skills.web_service.routes import router as web_router
from agent.skills.web_service.service import WebService
from agent.rate_limit import SlidingWindowRateLimiter
from agent.skills_engine import SkillEngine, SkillStateRepository
from agent.automation import AutomationRepository
from agent.automation_runner import AutomationRunner
from agent.mcp_adapter import MCPAdapter


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
    execution_journal = ExecutionJournalRepository(pool=pool)
    execution_journal.setup()
    skill_state_repo = SkillStateRepository(pool=pool)
    skill_state_repo.setup()
    skill_engine = SkillEngine.load(repository=skill_state_repo)
    automation_repo = AutomationRepository(pool=pool)
    automation_repo.setup()
    mcp_adapter = MCPAdapter(servers_json=settings.mcp_servers_json, timeout_seconds=settings.request_timeout_seconds)

    checkpointer_cm = PostgresSaver.from_conn_string(settings.postgres_uri)
    checkpointer = checkpointer_cm.__enter__()
    checkpointer.setup()

    tool_gateway = N8nToolGatewayClient(
        url=settings.tool_gateway_url,
        token=settings.tool_gateway_token,
        timeout_seconds=settings.request_timeout_seconds,
        learning_repo=learning_repo,
        approval_repo=approval_repo,
        execution_journal=execution_journal,
    )
    media_service = MediaService(settings=settings, learning_repo=learning_repo)
    web_service = WebService(settings=settings, memory_repo=memory_repo)

    app.state.settings = settings
    app.state.pool = pool
    app.state.memory_repo = memory_repo
    app.state.learning_repo = learning_repo
    app.state.approval_repo = approval_repo
    app.state.execution_journal = execution_journal
    app.state.skill_state_repo = skill_state_repo
    app.state.skill_engine = skill_engine
    app.state.automation_repo = automation_repo
    app.state.mcp_adapter = mcp_adapter
    app.state.checkpointer_cm = checkpointer_cm
    app.state.checkpointer = checkpointer
    app.state.media_service = media_service
    app.state.web_service = web_service
    agent_service = MiaAgentService(
        settings=settings,
        memory_repo=memory_repo,
        learning_repo=learning_repo,
        tool_gateway=tool_gateway,
        checkpointer=checkpointer,
        skill_engine=skill_engine,
    )
    app.state.agent_service = agent_service
    automation_runner = AutomationRunner(
        repository=automation_repo,
        service=agent_service,
        poll_seconds=settings.automation_poll_seconds,
    )
    automation_task = asyncio.create_task(automation_runner.run(), name="mia-automation-runner")
    app.state.automation_runner = automation_runner
    app.state.rate_limiter = SlidingWindowRateLimiter(
        limit=settings.api_rate_limit_per_minute,
        window_seconds=60,
    )

    try:
        yield
    finally:
        automation_runner.stop()
        automation_task.cancel()
        await asyncio.gather(automation_task, return_exceptions=True)
        checkpointer_cm.__exit__(None, None, None)
        pool.close()


app = FastAPI(title="Mia LangChain Core", lifespan=lifespan)
app.include_router(media_router)
app.include_router(web_router)


@app.middleware("http")
async def require_core_api_token(request: Request, call_next):
    path = request.url.path or "/"
    public = path in {"/health", "/mia/media/health", "/mia/web/health"}
    protected = path.startswith("/mia/") and not public
    if not protected:
        return await call_next(request)

    settings: Settings | None = getattr(request.app.state, "settings", None)
    expected_token = (settings.core_api_token if settings else "").strip()
    if not expected_token:
        return JSONResponse(status_code=503, content={"detail": "Mia core auth is not configured."})

    auth_header = str(request.headers.get("authorization") or "").strip()
    bearer_token = auth_header[7:].strip() if auth_header.lower().startswith("bearer ") else ""
    provided_token = str(request.headers.get("x-mia-core-token") or bearer_token).strip()
    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        return JSONResponse(status_code=401, content={"detail": "Unauthorized mia-core token."})

    limiter: SlidingWindowRateLimiter | None = getattr(request.app.state, "rate_limiter", None)
    if limiter is not None:
        identity = str(request.headers.get("x-mia-user-id") or "").strip()
        if not identity:
            identity = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.allow(f"{identity}:{path}")
        if not allowed:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={"detail": "Rate limit exceeded.", "retry_after_seconds": retry_after},
            )

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
        "executions": app.state.execution_journal.summary(days=max(1, int(days or 7))),
        "skills": app.state.skill_state_repo.summary(days=max(1, int(days or 7))),
        "automations": app.state.automation_repo.summary(),
    }


@app.post("/mia/automation/create")
def automation_create(request: MiaAutomationRequest) -> dict[str, object]:
    if not request.name or not request.schedule or not request.skill_name:
        return {"ok": False, "text": "Automation name, schedule, and skill name are required."}
    try:
        row = app.state.automation_repo.create(
            chat_id=request.chat_id,
            user_id=request.user_id,
            name=request.name,
            schedule=request.schedule,
            skill_name=request.skill_name,
            input_text=request.input_text,
            next_run_at=request.next_run_at,
        )
    except ValueError as exc:
        return {"ok": False, "text": str(exc), "result": {}}
    return {"ok": True, "text": f"Automation created: {request.name}", "result": row}


@app.post("/mia/automation/list")
def automation_list(request: MiaAutomationRequest) -> dict[str, object]:
    rows = app.state.automation_repo.list(user_id=request.user_id)
    text = "\n".join(f"{row['id']}. {row['name']} | {row['schedule']} | {'active' if row['enabled'] else 'paused'}" for row in rows)
    return {"ok": True, "text": text or "No automations configured.", "result": rows}


@app.post("/mia/automation/pause")
def automation_pause(request: MiaAutomationActionRequest) -> dict[str, object]:
    row = app.state.automation_repo.set_enabled(automation_id=request.automation_id, user_id=request.user_id, enabled=False)
    return {"ok": bool(row), "text": "Automation paused." if row else "Automation not found.", "result": row or {}}


@app.post("/mia/automation/resume")
def automation_resume(request: MiaAutomationActionRequest) -> dict[str, object]:
    row = app.state.automation_repo.set_enabled(automation_id=request.automation_id, user_id=request.user_id, enabled=True)
    return {"ok": bool(row), "text": "Automation resumed." if row else "Automation not found.", "result": row or {}}


@app.post("/mia/automation/delete")
def automation_delete(request: MiaAutomationActionRequest) -> dict[str, object]:
    deleted = app.state.automation_repo.delete(automation_id=request.automation_id, user_id=request.user_id)
    return {"ok": deleted, "text": "Automation deleted." if deleted else "Automation not found.", "result": {"id": request.automation_id}}


@app.post("/mia/automation/run-now")
def automation_run_now(request: MiaAutomationActionRequest) -> dict[str, object]:
    row = app.state.automation_repo.get(automation_id=request.automation_id, user_id=request.user_id)
    if not row:
        return {"ok": False, "text": "Automation not found."}
    service: MiaAgentService = app.state.agent_service
    response = service.chat(
        MiaChatRequest(
            chat_id=request.chat_id,
            user_id=request.user_id,
            text=str(row.get("input_text") or row.get("skill_name") or row.get("name")),
            metadata={"automation_id": row["id"], "skill_name": row["skill_name"]},
        )
    )
    app.state.automation_repo.touch_run(automation_id=request.automation_id)
    return {"ok": response.ok, "text": response.final_text, "result": response.model_dump(mode="json")}


@app.post("/mia/mcp/tools")
def mcp_list_tools(request: MiaMCPCallRequest) -> dict[str, object]:
    try:
        tools = app.state.mcp_adapter.list_tools(request.server)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "text": f"{len(tools)} allowlisted MCP tools.", "result": tools}


@app.post("/mia/mcp/call")
def mcp_call_tool(request: MiaMCPCallRequest) -> dict[str, object]:
    try:
        result = app.state.mcp_adapter.call_read_only_tool(request.server, request.tool, request.arguments)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {"ok": True, "text": str(result.get("text") or result), "result": result}
