from __future__ import annotations

from typing import Any

from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _normalize_instruction, _run_gateway_tool, _with_instruction_fallback


def get_github_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool("github_get_repo")
    def github_get_repo_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get repository metadata from GitHub."""
        text = _normalize_instruction("github", "xem repo", instruction or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_repo",
            _with_instruction_fallback("github", "xem repo", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"]),
            runtime,
        )

    @tool("github_get_repo_tree")
    def github_get_repo_tree_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        path: str = "",
        ref: str = "",
        limit: int = 20,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List the repository structure or the contents of a specific directory in a GitHub repository."""
        text = _normalize_instruction("github", "xem cau truc repo", instruction or path or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "path": path.strip(),
            "ref": ref.strip(),
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_repo_tree",
            _with_instruction_fallback("github", "xem cau truc repo", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["path"], payload["ref"], payload["limit"]),
            runtime,
        )

    @tool("github_help")
    def github_help_tool(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Show GitHub capabilities and usage examples."""
        return _run_gateway_tool(tool_gateway, "github.help", {}, runtime)

    @tool("github_list_user_repos")
    def github_list_user_repos_tool(
        username: str = "",
        visibility: str = "",
        limit: int = 20,
        page: int = 1,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List repositories for the authenticated GitHub account or a specific user."""
        text = _normalize_instruction("github", "xem repo cua minh", instruction or username)
        payload = {
            "username": username.strip(),
            "visibility": visibility.strip(),
            "limit": max(1, min(limit, 100)),
            "page": max(1, page),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_user_repos",
            _with_instruction_fallback("github", "xem repo cua minh", payload, text, payload["username"], payload["visibility"], payload["limit"], payload["page"]),
            runtime,
        )

    @tool("github_search_repos")
    def github_search_repos_tool(
        query: str = "",
        topic: str = "",
        language: str = "",
        sort_by: str = "",
        limit: int = 10,
        page: int = 1,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search GitHub repositories by topic, language, stars, forks, or update time."""
        text = _normalize_instruction("github", "tim repo", instruction or query or topic or language)
        payload = {
            "query": query.strip(),
            "topic": topic.strip(),
            "language": language.strip(),
            "sortBy": sort_by.strip(),
            "limit": max(1, min(limit, 100)),
            "page": max(1, page),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.search_repos",
            _with_instruction_fallback("github", "tim repo", payload, text, payload["query"], payload["topic"], payload["language"], payload["sortBy"], payload["limit"], payload["page"]),
            runtime,
        )

    @tool("github_list_branches")
    def github_list_branches_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        limit: int = 20,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List branches in a GitHub repository."""
        text = _normalize_instruction("github", "xem branch", instruction or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_branches",
            _with_instruction_fallback("github", "xem branch", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["limit"]),
            runtime,
        )

    @tool("github_list_commits")
    def github_list_commits_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        limit: int = 20,
        ref: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List commits in a GitHub repository."""
        text = _normalize_instruction("github", "xem commit", instruction or repo or repo_url or owner or repo_name or ref)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "ref": ref.strip(),
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_commits",
            _with_instruction_fallback("github", "xem commit", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["ref"], payload["limit"]),
            runtime,
        )

    @tool("github_get_commit")
    def github_get_commit_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        ref: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get a specific GitHub commit by SHA or ref."""
        text = _normalize_instruction("github", "xem chi tiet commit", instruction or repo or repo_url or owner or repo_name or ref)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "ref": ref.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_commit",
            _with_instruction_fallback("github", "xem chi tiet commit", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["ref"]),
            runtime,
        )

    @tool("github_list_releases")
    def github_list_releases_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        limit: int = 10,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List releases for a GitHub repository."""
        text = _normalize_instruction("github", "xem releases", instruction or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_releases",
            _with_instruction_fallback("github", "xem releases", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["limit"]),
            runtime,
        )

    @tool("github_get_release")
    def github_get_release_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        tag: str = "",
        release_id: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get a GitHub release by tag or release id."""
        text = _normalize_instruction("github", "xem release", instruction or tag or release_id or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "tag": tag.strip(),
            "releaseId": release_id.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_release",
            _with_instruction_fallback("github", "xem release", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["tag"], payload["releaseId"]),
            runtime,
        )

    @tool("github_list_pull_requests")
    def github_list_pull_requests_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        state: str = "open",
        limit: int = 10,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List pull requests for a GitHub repository."""
        text = _normalize_instruction("github", "xem pull requests", instruction or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "state": state.strip() or "open",
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_pull_requests",
            _with_instruction_fallback("github", "xem pull requests", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["state"], payload["limit"]),
            runtime,
        )

    @tool("github_get_pull_request")
    def github_get_pull_request_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        number: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get a specific GitHub pull request by number."""
        text = _normalize_instruction("github", "xem pull request", instruction or number or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "number": number.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_pull_request",
            _with_instruction_fallback("github", "xem pull request", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["number"]),
            runtime,
        )

    @tool("github_list_issues")
    def github_list_issues_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        state: str = "open",
        labels: str = "",
        limit: int = 10,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """List issues for a GitHub repository."""
        text = _normalize_instruction("github", "xem issues", instruction or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "state": state.strip() or "open",
            "labels": labels.strip(),
            "limit": max(1, min(limit, 100)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.list_issues",
            _with_instruction_fallback("github", "xem issues", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["state"], payload["labels"], payload["limit"]),
            runtime,
        )

    @tool("github_get_issue")
    def github_get_issue_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        number: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get a specific GitHub issue by number."""
        text = _normalize_instruction("github", "xem issue", instruction or number or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "number": number.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_issue",
            _with_instruction_fallback("github", "xem issue", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["number"]),
            runtime,
        )

    @tool("github_get_file")
    def github_get_file_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        path: str = "",
        ref: str = "",
        max_chars: int = 4000,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read a file from a GitHub repository."""
        text = _normalize_instruction("github", "doc file", instruction or path or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "path": path.strip(),
            "ref": ref.strip(),
            "maxChars": max(0, int(max_chars or 0)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_file",
            _with_instruction_fallback("github", "doc file", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["path"], payload["ref"], payload["maxChars"]),
            runtime,
        )

    @tool("github_search_code")
    def github_search_code_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        query: str = "",
        limit: int = 10,
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search for code in a GitHub repository."""
        text = _normalize_instruction("github", "tim code", instruction or query or repo or repo_url or owner or repo_name)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "query": query.strip(),
            "limit": max(1, min(limit, 10)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.search_code",
            _with_instruction_fallback("github", "tim code", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["query"], payload["limit"]),
            runtime,
        )

    @tool("github_get_diff")
    def github_get_diff_tool(
        repo: str = "",
        owner: str = "",
        repo_name: str = "",
        repo_url: str = "",
        base: str = "",
        head: str = "",
        instruction: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get a GitHub diff between two refs."""
        text = _normalize_instruction("github", "xem diff", instruction or repo or repo_url or owner or repo_name or base or head)
        payload = {
            "repo": repo.strip(),
            "owner": owner.strip(),
            "repoName": repo_name.strip(),
            "repoUrl": repo_url.strip(),
            "base": base.strip(),
            "head": head.strip(),
        }
        return _run_gateway_tool(
            tool_gateway,
            "github.get_diff",
            _with_instruction_fallback("github", "xem diff", payload, text, payload["repo"], payload["owner"], payload["repoName"], payload["repoUrl"], payload["base"], payload["head"]),
            runtime,
        )

    return [
        github_get_repo_tool,
        github_get_repo_tree_tool,
        github_help_tool,
        github_list_user_repos_tool,
        github_search_repos_tool,
        github_list_branches_tool,
        github_list_commits_tool,
        github_get_commit_tool,
        github_list_releases_tool,
        github_get_release_tool,
        github_list_pull_requests_tool,
        github_get_pull_request_tool,
        github_list_issues_tool,
        github_get_issue_tool,
        github_get_file_tool,
        github_search_code_tool,
        github_get_diff_tool,
    ]
