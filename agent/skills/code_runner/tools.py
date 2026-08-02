from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain.tools import ToolRuntime, tool

from agent.config import Settings
from agent.i18n import t
from agent.models import MiaContext
from agent.skills.code_runner.client import CodeRunnerClient, CodeRunnerError


def _client() -> CodeRunnerClient:
    settings = Settings.from_env()
    return CodeRunnerClient(
        base_url=settings.code_gateway_url,
        token=settings.code_gateway_token,
        timeout_seconds=settings.code_timeout_seconds,
    )


def _format_result(data: dict[str, Any]) -> str:
    text = str(data.get("text") or "").strip()
    if text:
        return text
    return json.dumps(data, ensure_ascii=False, indent=2)


def _run(endpoint: str, payload: dict[str, Any]) -> str:
    try:
        return _format_result(_client().request(endpoint, payload))
    except CodeRunnerError as exc:
        return f"Code runner chưa thực hiện được thao tác này: {exc}"


def _translate_host_source_path(source_path: str) -> str:
    raw = str(source_path or "").strip()
    if not raw:
        return raw
    try:
        path = Path(raw).expanduser().resolve()
        host_root = Path(os.getenv("MIA_CODE_HOST_PROJECTS_ROOT", "/home/huynhminh/Projects")).expanduser().resolve()
        container_root = Path(os.getenv("MIA_CODE_CONTAINER_PROJECTS_ROOT", "/host-projects")).resolve()
        relative = path.relative_to(host_root)
    except (OSError, ValueError):
        return raw
    return str(container_root / relative)


def get_code_tools(default_project_id: str = "", tool_gateway: Any | None = None) -> list:
    default_project_id = str(default_project_id or "").strip()

    def resolve_project_id(project_id: str = "") -> str:
        return str(project_id or "").strip() or default_project_id

    def _run_code_guarded(
        *,
        gateway_tool_name: str,
        endpoint: str,
        payload: dict[str, Any],
        runtime: ToolRuntime[MiaContext] | None,
    ) -> str:
        approval_repo = getattr(tool_gateway, "approval_repo", None) if tool_gateway is not None else None
        if approval_repo is None:
            return _run(endpoint, payload)
        context = getattr(runtime, "context", None)
        if context is None:
            return t(
                "error.approval_required",
                summary=gateway_tool_name,
                confirm_keyword=t("error.approval_confirm_keyword"),
            )
        pending = approval_repo.create_pending_action(
            chat_id=context.chat_id,
            user_id=context.user_id,
            request_id=context.request_id,
            tool_name=gateway_tool_name,
            gateway_name=gateway_tool_name,
            args={"endpoint": endpoint, "payload": payload},
            reason="dangerous code action requires explicit confirmation",
            summary=gateway_tool_name,
        )
        summary = str(pending.get("summary") or gateway_tool_name).strip()
        return t(
            "error.approval_required",
            summary=summary,
            confirm_keyword=t("error.approval_confirm_keyword"),
        )

    @tool("code_create_project")
    def create_project(project_name: str, instruction: str = "", title: str = "") -> str:
        """Create a new dedicated code workspace in Mia's managed workspace root and optionally start coding."""
        return _run(
            "projects/create",
            {
                "project_name": project_name,
                "instruction": instruction,
                "title": title,
            },
        )

    @tool("code_import_existing_project")
    def import_existing_project(source_path: str, project_name: str = "", instruction: str = "", title: str = "") -> str:
        """Import an existing local project into Mia's managed coding sandbox, then optionally work on it."""
        return _run(
            "projects/import",
            {
                "source_path": _translate_host_source_path(source_path),
                "project_name": project_name,
                "instruction": instruction,
                "title": title,
            },
        )

    @tool("code_work_on_project")
    def work_on_project(project_id: str = "", instruction: str = "") -> str:
        """Continue coding on a managed project. If project_id is omitted and only one project exists, Mia will use it."""
        return _run("projects/work", {"project_id": resolve_project_id(project_id), "instruction": instruction})

    @tool("code_project_status")
    def project_status(project_id: str = "") -> str:
        """Show status for one managed code project, or all projects if project_id is omitted."""
        return _run("projects/status", {"project_id": resolve_project_id(project_id)})

    @tool("code_project_diff")
    def project_diff(project_id: str = "", max_chars: int = 30000) -> str:
        """Show the current git diff for one managed code project."""
        return _run("projects/diff", {"project_id": resolve_project_id(project_id), "max_chars": max_chars})

    @tool("code_review_project")
    def review_project(project_id: str = "", focus: str = "") -> str:
        """Review the current changes of a managed code project for bugs, security, and performance."""
        return _run(
            "projects/review",
            {"project_id": resolve_project_id(project_id), "scope": "diff", "focus": focus},
        )

    @tool("code_optimize_project")
    def optimize_project(project_id: str = "", focus: str = "") -> str:
        """Analyze a managed code project and propose performance and quality optimizations."""
        return _run(
            "projects/optimize",
            {"project_id": resolve_project_id(project_id), "focus": focus},
        )

    @tool("code_run_test")
    def run_test(project_id: str = "", test_args: str = "") -> str:
        """Run the test suite (pytest/npm test) inside a managed code project and return the result."""
        return _run(
            "projects/test",
            {"project_id": resolve_project_id(project_id), "test_args": test_args},
        )

    @tool("code_run_lint")
    def run_lint(project_id: str = "", tool: str = "auto", target: str = "") -> str:
        """Run a linter (ruff/mypy/npm run lint) inside a managed code project and return the result."""
        return _run(
            "projects/lint",
            {"project_id": resolve_project_id(project_id), "tool": tool, "target": target},
        )

    @tool("code_fix_from_issue")
    def fix_from_issue(
        project_id: str = "",
        repo: str = "",
        issue_number: str = "",
        issue_title: str = "",
        issue_body: str = "",
        base: str = "main",
        create_pr: bool = False,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Fix a GitHub issue in a managed code project: create a branch, edit, run tests. Opening a PR requires user confirmation."""
        payload = {
            "project_id": resolve_project_id(project_id),
            "repo": repo,
            "issue_number": issue_number,
            "issue_title": issue_title,
            "issue_body": issue_body,
            "base": base,
            "create_pr": create_pr,
        }
        if create_pr:
            return _run_code_guarded(
                gateway_tool_name="code.fix_from_issue",
                endpoint="projects/fix-issue",
                payload=payload,
                runtime=runtime,
            )
        return _run("projects/fix-issue", payload)

    @tool("code_apply_to_existing_project")
    def apply_to_existing_project(
        project_id: str = "",
        confirmed: bool = False,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Apply sandbox changes back to the original imported local project. Requires user confirmation."""
        return _run_code_guarded(
            gateway_tool_name="code.apply_to_existing_project",
            endpoint="projects/apply",
            payload={"project_id": resolve_project_id(project_id), "confirmed": True},
            runtime=runtime,
        )

    @tool("code_publish_project")
    def publish_project(
        project_id: str = "",
        title: str = "",
        body: str = "",
        branch: str = "",
        base: str = "main",
        mode: str = "push",
        confirmed: bool = False,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Push a managed project branch, or create a GitHub pull request. Requires user confirmation."""
        return _run_code_guarded(
            gateway_tool_name="code.publish_project",
            endpoint="projects/publish",
            payload={
                "project_id": resolve_project_id(project_id),
                "title": title,
                "body": body,
                "branch": branch,
                "base": base,
                "mode": mode,
                "confirmed": True,
            },
            runtime=runtime,
        )

    return [
        create_project,
        import_existing_project,
        work_on_project,
        project_status,
        project_diff,
        review_project,
        optimize_project,
        run_test,
        run_lint,
        fix_from_issue,
        apply_to_existing_project,
        publish_project,
    ]
