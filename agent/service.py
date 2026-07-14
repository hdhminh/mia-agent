from __future__ import annotations

from typing import Any

from langchain.agents import AgentState, create_agent
from langchain.agents.middleware import ModelRetryMiddleware, ToolRetryMiddleware, before_model
from langchain.messages import AIMessage, HumanMessage, RemoveMessage, SystemMessage
from langchain_core.messages import trim_messages
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.runtime import Runtime

from agent.skills import registry as caps
from agent.approval import is_cancellation_text, is_confirmation_text
from agent.config import Settings
from agent.brain.direct_executor import DirectExecutor, build_memory_recent_text
from agent.learning.repository import LearningRepository, build_learning_guidance_text, classify_learning_issue
from agent.error_envelope import ErrorEnvelope
from agent.brain.llm_provider import build_primary_and_fallback_models, normalize_llm_provider
from agent.memory.repository import MemoryRepository
from agent.models import MiaChatRequest, MiaChatResponse, MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.brain.prompt_cache import build_prompt_cache_key
from agent.brain.planner import looks_multi_step, normalize_query_text
from agent.brain.trace_utils import extract_prompt_cache_trace
from agent.brain.response_normalizer import (
    cap_visible_links as normalized_cap_visible_links,
    coerce_message_text as normalized_coerce_message_text,
    ensure_tool_links as normalized_ensure_tool_links,
    extract_tools_called as normalized_extract_tools_called,
    prefer_docs_search_output as normalized_prefer_docs_search_output,
    prefer_tool_truth as normalized_prefer_tool_truth,
    resolve_fallback_text as normalized_resolve_fallback_text,
    sanitize_final_text as normalized_sanitize_final_text,
)
from agent.brain.router import route_request
from agent.skills import build_tools
from agent.graph.builder import build_mia_graph
from agent.brain.capability_broker import CapabilityBroker
from agent.skills_engine import SkillEngine

from agent.persona.system_prompt import SYSTEM_PROMPT
from agent.i18n import t
from agent.skills.github_handler import GitHubHandler
from agent.brain.followup_handler import FollowupHandler
from agent.skills.code_runner.client import CodeRunnerClient, CodeRunnerError


def _build_trim_history_middleware(max_tokens: int):
    @before_model
    def trim_history(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = list(state.get("messages", []))
        if len(messages) <= 6:
            return None

        trimmed = trim_messages(
            messages,
            max_tokens=max_tokens,
            token_counter="approximate",
            strategy="last",
            start_on="human",
            allow_partial=False,
        )
        if len(trimmed) == len(messages):
            return None

        keep_ids = {msg.id for msg in trimmed if msg.id}
        remove_msgs = []
        for msg in messages:
            if msg.id not in keep_ids:
                remove_msgs.append(RemoveMessage(id=msg.id))
        if not remove_msgs:
            return None
        return {"messages": remove_msgs}

    return trim_history


class MiaAgentService:
    def __init__(
        self,
        *,
        settings: Settings,
        memory_repo: MemoryRepository,
        learning_repo: LearningRepository,
        tool_gateway: N8nToolGatewayClient,
        checkpointer: PostgresSaver,
        skill_engine: SkillEngine | None = None,
    ) -> None:
        self.settings = settings
        self.memory_repo = memory_repo
        self.learning_repo = learning_repo
        self.tool_gateway = tool_gateway
        self.checkpointer = checkpointer
        self.skill_engine = skill_engine
        self.primary_llm_provider = normalize_llm_provider(self.settings.primary_llm_provider)
        self.agent_models: dict[str, Any] = {}
        self.agent_fallback_models: dict[str, Any | None] = {}
        for name in caps.AGENT_TOOLSETS:
            primary, fallback = build_primary_and_fallback_models(
                self.settings,
                scope=f"agent:{name}",
                temperature=self.settings.temperature,
                max_tokens=self.settings.max_tokens,
            )
            self.agent_models[name] = primary
            self.agent_fallback_models[name] = fallback
        self.summary_model, self.summary_fallback_model = build_primary_and_fallback_models(
            self.settings,
            scope="agent:tool-summary",
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        self.document_followup_model, self.document_followup_fallback_model = build_primary_and_fallback_models(
            self.settings,
            scope="agent:document-followup",
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        self.model = self.agent_models["general"]
        self.tool_registry = self._build_tool_registry()
        self.capability_broker = CapabilityBroker.default()
        self._dynamic_agents: dict[tuple[str, tuple[str, ...]], Any] = {}
        self._dynamic_fallback_agents: dict[tuple[str, tuple[str, ...]], Any] = {}
        self.direct_executor = DirectExecutor(
            memory_repo=self.memory_repo,
            tool_gateway=self.tool_gateway,
        )
        self.code_runner_client = CodeRunnerClient(
            base_url=self.settings.code_gateway_url,
            token=self.settings.code_gateway_token,
            timeout_seconds=self.settings.code_timeout_seconds,
        )
        self.github_handler = GitHubHandler(self)
        self.followup_handler = FollowupHandler(self)
        self.agents = self._build_agents()
        self.fallback_agents = self._build_fallback_agents()
        self.graph = build_mia_graph(self, checkpointer=self.checkpointer)

    @staticmethod
    def _normalize_code_project_name(value: str) -> str:
        return normalize_query_text(str(value or "")).replace("/", " ").replace("_", " ").replace("-", " ").strip()

    def _resolve_active_code_project(self, request: MiaChatRequest) -> dict[str, Any]:
        if not self.settings.code_enabled:
            return {}
        metadata = request.metadata if isinstance(request.metadata, dict) else {}
        active = metadata.get("active_code_project")
        if isinstance(active, dict) and active.get("project_id"):
            return active
        try:
            projects = self.code_runner_client.list_projects()
        except CodeRunnerError:
            return {}
        if not projects:
            return {}
        if len(projects) == 1:
            return projects[0]

        normalized_text = self._normalize_code_project_name(request.text)
        if not normalized_text:
            return {}
        for project in projects:
            project_id = self._normalize_code_project_name(str(project.get("project_id") or ""))
            project_name = self._normalize_code_project_name(str(project.get("project_name") or ""))
            if project_id and project_id in normalized_text:
                return project
            if project_name and project_name in normalized_text:
                return project
        return {}

    def _enrich_request_metadata(self, request: MiaChatRequest) -> MiaChatRequest:
        metadata = dict(request.metadata or {})
        active_project = self._resolve_active_code_project(request)
        if active_project:
            metadata["active_code_project"] = active_project
        request.metadata = metadata
        return request

    @staticmethod
    def _learning_scopes(*, route_domain: str, agent_key: str, hint_tool: str) -> list[str]:
        scopes: list[str] = ["general"]
        for value in (route_domain, agent_key, hint_tool):
            clean = str(value or "").strip()
            if clean and clean not in scopes:
                scopes.append(clean)
        if route_domain == "media":
            for extra in ("media", "document", "image", "audio", "video"):
                if extra not in scopes:
                    scopes.append(extra)
        return scopes

    def _learning_guidance_text(self, *, scopes: list[str], limit: int = 4) -> str:
        if not self.learning_repo:
            return ""
        rows = self.learning_repo.list_active_insights(scopes=scopes, limit=limit)
        try:
            self.learning_repo.touch_insights([int(row["id"]) for row in rows if row.get("id") is not None])
        except Exception:
            pass
        return build_learning_guidance_text(rows, limit=limit)

    @staticmethod
    def _maybe_clarify_request(request: MiaChatRequest, route: Any) -> str:
        normalized = normalize_query_text(request.text)
        if route.domain != "google_full" or route.hint_tool:
            return ""
        if not looks_multi_step(request.text):
            return ""
        service_hints = [
            any(token in normalized for token in cues)
            for cues in (
                ("mail", "gmail", "email", "inbox", "hop thu", "hộp thư", "thư"),
                ("lich", "lịch", "calendar", "su kien", "sự kiện", "meeting"),
                ("drive", "folder", "thu muc", "thư mục", "file"),
                ("doc", "docs", "tai lieu", "tài liệu", "van ban", "văn bản"),
                ("sheet", "sheets", "bang tinh", "bảng tính"),
            )
        ]
        if sum(service_hints) < 2:
            return ""
        return t("clarify.google_full_clarify")

    def _try_pending_action_confirmation(
        self,
        request: MiaChatRequest,
        context: MiaContext,
    ) -> MiaChatResponse | None:
        approval_repo = getattr(self.tool_gateway, "approval_repo", None)
        if approval_repo is None:
            return None

        pending = approval_repo.latest_pending_action(
            chat_id=request.chat_id,
            user_id=request.resolved_user_id(),
        )
        if not pending:
            return None

        if is_cancellation_text(request.text):
            approval_repo.mark_pending_action_status(int(pending["id"]), "cancelled")
            if self.skill_engine is not None:
                try:
                    self.skill_engine.repository.finish_latest(
                        chat_id=request.chat_id,
                        user_id=request.resolved_user_id(),
                        status="cancelled",
                        state={"cancelled_action": pending.get("gateway_name") or pending.get("tool_name")},
                    )
                except Exception:
                    pass
            return MiaChatResponse(
                final_text=t("approval.cancelled", default="Đã hủy thao tác đang chờ."),
                tools_called=[],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={"approval": {"action_id": pending.get("id"), "status": "cancelled"}},
            )
        if not is_confirmation_text(request.text):
            return None

        try:
            result = self.tool_gateway.run_pending_action(
                pending,
                context,
                request_text=request.text,
            )
        except Exception as exc:
            tool_name = str(pending.get("gateway_name") or pending.get("tool_name") or "").strip()
            final_text = t("error.approval_failed", error=str(exc))
            response = MiaChatResponse(
                final_text=final_text,
                tools_called=[],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={"approval": {"action_id": pending.get("id"), "status": "failed", "tool": tool_name}},
            )
            self._record_learning_event(
                request=request,
                source="approval",
                scope=tool_name.split(".", 1)[0] if tool_name else "general",
                topic=tool_name or "approval",
                final_text=response.final_text,
                tools_called=[],
                trace=response.trace,
                notes="approved pending action failed",
            )
            return response

        tool_name = str(pending.get("gateway_name") or pending.get("tool_name") or "").strip()
        if not result.ok:
            error = result.error or ErrorEnvelope.build(
                code="tool_failed",
                category="external",
                severity="error",
                message=str(result.text or f"{tool_name} failed."),
                user_message=str(result.text or "Mia gặp lỗi từ tool gateway."),
                retryable=False,
                request_id=request.resolved_request_id(),
                thread_id=request.resolved_thread_id(),
                chat_id=request.chat_id,
                details={
                    "tool_name": tool_name,
                    "pending_action_id": pending.get("id"),
                },
            )
            response = MiaChatResponse(
                ok=False,
                final_text=error.display_text(),
                tools_called=[tool_name] if tool_name else [],
                thread_id=request.resolved_thread_id(),
                request_id=request.resolved_request_id(),
                trace={
                    "approval": {
                        "action_id": pending.get("id"),
                        "status": "failed",
                        "tool": tool_name,
                        "error": error.model_dump(mode="json"),
                    }
                },
                error=error,
            )
            self._record_learning_event(
                request=request,
                source="approval",
                scope=tool_name.split(".", 1)[0] if tool_name else "general",
                topic=tool_name or "approval",
                final_text=response.final_text,
                tools_called=response.tools_called,
                trace=response.trace,
                notes="approved pending action failed",
            )
            return response

        response_text = normalized_sanitize_final_text(
            result.text or str(pending.get("summary") or t("error.approval_done"))
        )
        response = MiaChatResponse(
            final_text=response_text,
            tools_called=[tool_name] if tool_name else [],
            thread_id=request.resolved_thread_id(),
            request_id=request.resolved_request_id(),
            trace={
                "approval": {
                    "action_id": pending.get("id"),
                    "status": str((result.payload or {}).get("status") if isinstance(result.payload, dict) else ""),
                    "tool": tool_name,
                }
            },
        )
        if self.skill_engine is not None:
            try:
                self.skill_engine.repository.finish_latest(
                    chat_id=request.chat_id,
                    user_id=request.resolved_user_id(),
                    status="completed",
                    state={"approved_action": tool_name, "final_text": response.final_text},
                )
            except Exception:
                pass
        self._record_learning_event(
            request=request,
            source="approval",
            scope=tool_name.split(".", 1)[0] if tool_name else "general",
            topic=tool_name or "approval",
            final_text=response.final_text,
            tools_called=response.tools_called,
            trace=response.trace,
            notes="approved pending action executed",
        )
        return response

    def _record_learning_event(
        self,
        *,
        request: MiaChatRequest,
        source: str,
        scope: str,
        topic: str,
        final_text: str,
        tools_called: list[str],
        trace: dict[str, Any],
        notes: str = "",
    ) -> None:
        if not self.learning_repo:
            return
        issue_type, severity, issue_note = classify_learning_issue(
            request_text=request.text,
            final_text=final_text,
            tools_called=tools_called,
            trace=trace,
            source=source,
            scope=scope,
            topic=topic,
        )
        merged_notes = "\n".join(part for part in [notes.strip(), issue_note.strip()] if part).strip()
        try:
            self.learning_repo.record_event(
                chat_id=request.chat_id,
                request_id=request.resolved_request_id(),
                thread_id=request.resolved_thread_id(),
                source=source,
                scope=scope,
                topic=topic,
                user_text=request.text,
                final_text=final_text,
                tools_called=tools_called,
                trace=trace,
                issue_type=issue_type,
                severity=severity,
                notes=merged_notes,
            )
        except Exception:
            pass

    def _build_model(self, *, cache_scope: str):  # legacy alias for callers/tests
        primary, _fallback = build_primary_and_fallback_models(
            self.settings,
            scope=cache_scope,
            temperature=self.settings.temperature,
            max_tokens=self.settings.max_tokens,
        )
        return primary

    def _prompt_cache_key(self, scope: str, *, provider_used: str = "primary") -> str:
        if not self.settings.prompt_cache_enabled:
            return ""
        provider_name = self.primary_llm_provider if provider_used != "fallback" else "openrouter"
        return build_prompt_cache_key(
            namespace=self.settings.prompt_cache_namespace,
            scope=f"{provider_name}:{scope}",
            version=self.settings.prompt_cache_version,
        )

    def _trace_model_name(self, provider_used: str) -> str:
        if self.primary_llm_provider == "deepseek_direct" and provider_used == "primary":
            return self.settings.deepseek_model
        return self.settings.model

    def _cache_trace(self, message: Any, *, scope: str, provider_used: str = "primary") -> dict[str, Any]:
        return extract_prompt_cache_trace(
            message,
            scope=scope,
            model=self._trace_model_name(provider_used),
            prompt_cache_key=self._prompt_cache_key(scope, provider_used=provider_used),
        )

    def _build_tool_registry(self, *, code_default_project_id: str = "") -> dict[str, Any]:
        tools = build_tools(
            memory_repo=self.memory_repo,
            tool_gateway=self.tool_gateway,
            code_default_project_id=code_default_project_id,
        )
        return {tool.name: tool for tool in tools}

    def _build_agent(self, *, tool_names: list[str], model: Any, code_default_project_id: str = ""):
        tool_registry = self.tool_registry
        if code_default_project_id:
            tool_registry = self._build_tool_registry(code_default_project_id=code_default_project_id)
        tools = [tool_registry[name] for name in tool_names]
        return create_agent(
            model=model,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            context_schema=MiaContext,
            checkpointer=None,
            middleware=[
                _build_trim_history_middleware(self.settings.history_max_tokens),
                ModelRetryMiddleware(max_retries=1),
                ToolRetryMiddleware(max_retries=1),
            ],
        )

    def _build_agents(self) -> dict[str, Any]:
        return {
            name: self._build_agent(tool_names=tool_names, model=self.agent_models[name])
            for name, tool_names in caps.AGENT_TOOLSETS.items()
        }

    def _build_fallback_agents(self) -> dict[str, Any]:
        fallback_agents: dict[str, Any] = {}
        for name, tool_names in caps.AGENT_TOOLSETS.items():
            fallback_model = self.agent_fallback_models.get(name)
            if fallback_model is None:
                continue
            fallback_agents[name] = self._build_agent(tool_names=tool_names, model=fallback_model)
        return fallback_agents

    def _invoke_agent_with_fallback(
        self,
        *,
        agent_key: str,
        messages_payload: list[dict[str, str]],
        thread_id: str,
        context: MiaContext,
        query: str = "",
        hint_tool: str = "",
        request_metadata: dict[str, Any] | None = None,
    ):
        available = caps.AGENT_TOOLSETS[agent_key]
        selected = self.capability_broker.select_tool_names(
            query=query,
            domain=agent_key,
            available=available,
            hint_tool=hint_tool,
            limit=14 if agent_key == "code" else 12 if agent_key == "google_full" else 10,
        )
        recursion_limit = max(self.settings.recursion_limit, 28) if agent_key == "code" else self.settings.recursion_limit
        code_default_project_id = ""
        if agent_key == "code" and isinstance(request_metadata, dict):
            active_project = request_metadata.get("active_code_project")
            if isinstance(active_project, dict):
                code_default_project_id = str(active_project.get("project_id") or "").strip()
        cache_key = (agent_key, tuple(selected), code_default_project_id)
        agent = self._dynamic_agents.get(cache_key)
        if agent is None:
            agent = self._build_agent(
                tool_names=selected,
                model=self.agent_models[agent_key],
                code_default_project_id=code_default_project_id,
            )
            self._dynamic_agents[cache_key] = agent
        try:
            return agent.invoke(
                {"messages": messages_payload},
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": recursion_limit,
                },
                context=context,
            ), "primary"
        except Exception as primary_exc:
            fallback_agent = self._dynamic_fallback_agents.get(cache_key)
            fallback_model = self.agent_fallback_models.get(agent_key)
            if fallback_agent is None and fallback_model is not None:
                fallback_agent = self._build_agent(
                    tool_names=selected,
                    model=fallback_model,
                    code_default_project_id=code_default_project_id,
                )
                self._dynamic_fallback_agents[cache_key] = fallback_agent
            if fallback_agent is None:
                raise
            try:
                return fallback_agent.invoke(
                    {"messages": messages_payload},
                    config={
                        "configurable": {"thread_id": thread_id},
                        "recursion_limit": recursion_limit,
                    },
                    context=context,
                ), "fallback"
            except Exception:
                raise primary_exc

    def _invoke_model_with_fallback(
        self,
        primary_model: Any,
        fallback_model: Any | None,
        messages: list[Any],
        *,
        scope: str,
    ):
        try:
            result = primary_model.invoke(messages)
            return result, "primary"
        except Exception as primary_exc:
            if fallback_model is None:
                raise
            try:
                result = fallback_model.invoke(messages)
                return result, "fallback"
            except Exception:
                raise primary_exc

    def _try_direct_route(
        self,
        request: MiaChatRequest,
        context: MiaContext,
        hint_tool: str,
        *,
        allow_multistep: bool = False,
    ) -> MiaChatResponse | None:
        return self.direct_executor.execute(
            request,
            context,
            hint_tool,
            allow_multistep=allow_multistep,
        )

    def _summarize_tool_result(self, user_text: str, tool_text: str) -> tuple[str, dict[str, Any]]:
        result, provider_used = self._invoke_model_with_fallback(
            self.summary_model,
            self.summary_fallback_model,
            [
                SystemMessage(
                    content=t("skills.summary_prompt_system")
                ),
                HumanMessage(
                    content=t(
                        "skills.summary_prompt_human",
                        user_text=user_text,
                        tool_text=tool_text,
                    )
                ),
            ],
            scope="agent:tool-summary",
        )
        summary_text = normalized_sanitize_final_text(normalized_coerce_message_text(result.content))
        summary_trace = self._cache_trace(result, scope="agent:tool-summary", provider_used=provider_used)
        summary_trace["provider"] = provider_used
        return summary_text, summary_trace

    def _try_document_memory_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        return self.followup_handler._try_document_memory_followup(request)

    def _try_url_memory_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        return self.followup_handler._try_url_memory_followup(request)

    def _try_github_selected_repo_followup(self, request: MiaChatRequest, context: MiaContext) -> MiaChatResponse | None:
        return self.github_handler._try_github_selected_repo_followup(request, context)

    def _try_github_search_followup(self, request: MiaChatRequest) -> MiaChatResponse | None:
        return self.github_handler._try_github_search_followup(request)

    def chat(self, request: MiaChatRequest) -> MiaChatResponse:
        request = self._enrich_request_metadata(request)
        thread_id = request.resolved_thread_id()
        request_id = request.resolved_request_id()
        context = MiaContext(
            chat_id=request.chat_id,
            user_id=request.resolved_user_id(),
            timezone=self.settings.timezone,
            request_id=request_id,
        )

        initial_state = {
            "request": request,
            "context": context,
            "thread_id": thread_id,
            "request_id": request_id,
            "retry_count": 0,
            "messages": [],
            "tools_called": [],
            "evidence": [],
            "pending_memory_writes": [],
            "memory_written": False,
        }

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": self.settings.recursion_limit * 2,
        }
        try:
            final_state = self.graph.invoke(initial_state, config=config)
            return final_state["response"]
        except GraphRecursionError:
            # Fallback if graph exceeds recursion limit
            fallback_response = self._try_direct_route(
                request,
                context,
                None,
                allow_multistep=True,
            )
            if fallback_response is not None:
                return fallback_response
            raise
