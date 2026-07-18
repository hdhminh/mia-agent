from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from langchain.tools import tool

from agent.config import Settings
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


def get_code_tools(default_project_id: str = "") -> list:
    default_project_id = str(default_project_id or "").strip()

    def resolve_project_id(project_id: str = "") -> str:
        return str(project_id or "").strip() or default_project_id

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

    @tool("code_apply_to_existing_project")
    def apply_to_existing_project(project_id: str = "", confirmed: bool = False) -> str:
        """Apply sandbox changes back to the original imported local project after explicit approval."""
        return _run("projects/apply", {"project_id": resolve_project_id(project_id), "confirmed": confirmed})

    @tool("code_publish_project")
    def publish_project(
        project_id: str = "",
        title: str = "",
        body: str = "",
        branch: str = "",
        base: str = "main",
        mode: str = "push",
        confirmed: bool = False,
    ) -> str:
        """Push a managed project branch, or create a GitHub pull request, after explicit approval."""
        return _run(
            "projects/publish",
            {
                "project_id": resolve_project_id(project_id),
                "title": title,
                "body": body,
                "branch": branch,
                "base": base,
                "mode": mode,
                "confirmed": confirmed,
            },
        )

    return [
        create_project,
        import_existing_project,
        work_on_project,
        project_status,
        project_diff,
        apply_to_existing_project,
        publish_project,
    ]
