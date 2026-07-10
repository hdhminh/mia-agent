from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.execution_client import N8nToolGatewayClient
from agent.models import MiaContext
from agent.skills.common import _run_gateway_tool


def get_github_write_tools(tool_gateway: N8nToolGatewayClient) -> list:
    def run(action: str, payload: dict, runtime: ToolRuntime[MiaContext]) -> str:
        return _run_gateway_tool(tool_gateway, action, payload, runtime)

    @tool("github_create_issue")
    def create_issue(repo: str, title: str, body: str = "", labels: list[str] | None = None, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create a GitHub issue after approval."""
        return run("github.create_issue", {"repo": repo, "title": title, "body": body, "labels": labels or []}, runtime)

    @tool("github_update_issue")
    def update_issue(repo: str, number: int, title: str = "", body: str = "", state: str = "", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Update a GitHub issue after approval."""
        return run("github.update_issue", {"repo": repo, "number": number, "title": title, "body": body, "state": state}, runtime)

    @tool("github_comment_issue")
    def comment_issue(repo: str, number: int, body: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Comment on a GitHub issue after approval."""
        return run("github.comment_issue", {"repo": repo, "number": number, "body": body}, runtime)

    @tool("github_create_branch")
    def create_branch(repo: str, branch: str, source_sha: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create a GitHub branch from an existing commit SHA after approval."""
        return run("github.create_branch", {"repo": repo, "branch": branch, "sourceSha": source_sha}, runtime)

    @tool("github_update_file")
    def update_file(repo: str, path: str, content_base64: str, message: str, branch: str, sha: str = "", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create or update a GitHub file after approval; content must be base64 encoded."""
        return run("github.update_file", {"repo": repo, "path": path, "content": content_base64, "message": message, "branch": branch, "sha": sha}, runtime)

    @tool("github_create_pull_request")
    def create_pull_request(repo: str, title: str, head: str, base: str = "main", body: str = "", draft: bool = True, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create a GitHub pull request after approval."""
        return run("github.create_pull_request", {"repo": repo, "title": title, "head": head, "base": base, "body": body, "draft": draft}, runtime)

    @tool("github_comment_pull_request")
    def comment_pull_request(repo: str, number: int, body: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Comment on a pull request after approval."""
        return run("github.comment_pull_request", {"repo": repo, "number": number, "body": body}, runtime)

    @tool("github_list_workflow_runs")
    def list_workflow_runs(repo: str, branch: str = "", status: str = "", limit: int = 10, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """List GitHub Actions workflow runs."""
        return run("github.list_workflow_runs", {"repo": repo, "branch": branch, "status": status, "limit": max(1, min(limit, 50))}, runtime)

    @tool("github_rerun_failed_workflow")
    def rerun_failed_workflow(repo: str, run_id: int, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Rerun failed jobs in a GitHub Actions run after approval."""
        return run("github.rerun_failed_workflow", {"repo": repo, "runId": run_id}, runtime)

    return [create_issue, update_issue, comment_issue, create_branch, update_file, create_pull_request,
            comment_pull_request, list_workflow_runs, rerun_failed_workflow]
