from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _run_gateway_tool, _normalize_instruction


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
        return _run_gateway_tool(
            tool_gateway,
            "github.get_repo",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.get_repo_tree",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "path": path.strip(),
                "ref": ref.strip(),
                "limit": max(1, min(limit, 100)),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.list_user_repos",
            {
                "username": username.strip(),
                "visibility": visibility.strip(),
                "limit": max(1, min(limit, 100)),
                "page": max(1, page),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.search_repos",
            {
                "query": query.strip(),
                "topic": topic.strip(),
                "language": language.strip(),
                "sortBy": sort_by.strip(),
                "limit": max(1, min(limit, 100)),
                "page": max(1, page),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.list_branches",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "limit": max(1, min(limit, 100)),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.list_commits",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "ref": ref.strip(),
                "limit": max(1, min(limit, 100)),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.get_commit",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "ref": ref.strip(),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.get_file",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "path": path.strip(),
                "ref": ref.strip(),
                "maxChars": max(0, int(max_chars or 0)),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.search_code",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "query": query.strip(),
                "limit": max(1, min(limit, 10)),
                "instruction": text,
            },
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
        return _run_gateway_tool(
            tool_gateway,
            "github.get_diff",
            {
                "repo": repo.strip(),
                "owner": owner.strip(),
                "repoName": repo_name.strip(),
                "repoUrl": repo_url.strip(),
                "base": base.strip(),
                "head": head.strip(),
                "instruction": text,
            },
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
        github_get_file_tool,
        github_search_code_tool,
        github_get_diff_tool,
    ]
