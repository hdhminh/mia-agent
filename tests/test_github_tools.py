from __future__ import annotations

import unittest
from dataclasses import dataclass

from agent.models import MiaContext
from agent.skills.github import get_github_tools


@dataclass
class _DummyGatewayResult:
    text: str


class _DummyGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def run_tool(self, tool_name: str, args: dict[str, object], _context: MiaContext) -> _DummyGatewayResult:
        self.calls.append((tool_name, dict(args)))
        return _DummyGatewayResult(text="ok")


class _DummyRuntime:
    def __init__(self) -> None:
        self.context = MiaContext(
            chat_id="chat-1",
            user_id="user-1",
            timezone="Asia/Ho_Chi_Minh",
            request_id="req-1",
        )


class GitHubToolStructuredPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.gateway = _DummyGateway()
        self.runtime = _DummyRuntime()
        self.tools = {tool.name: tool for tool in get_github_tools(self.gateway)}

    def test_github_list_releases_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_list_releases"].func(  # type: ignore[union-attr]
            repo="octocat/hello-world",
            limit=5,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.list_releases")
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["limit"], 5)
        self.assertNotIn("instruction", args)

    def test_github_get_release_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_get_release"].func(  # type: ignore[union-attr]
            repo="octocat/hello-world",
            release_id="latest",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.get_release")
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["releaseId"], "latest")
        self.assertNotIn("instruction", args)

    def test_github_list_pull_requests_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_list_pull_requests"].func(  # type: ignore[union-attr]
            repo="octocat/hello-world",
            state="open",
            limit=10,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.list_pull_requests")
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["state"], "open")
        self.assertEqual(args["limit"], 10)
        self.assertNotIn("instruction", args)

    def test_github_get_issue_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_get_issue"].func(  # type: ignore[union-attr]
            repo="octocat/hello-world",
            number="7",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.get_issue")
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["number"], "7")
        self.assertNotIn("instruction", args)

    def test_github_get_repo_tree_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_get_repo_tree"].func(  # type: ignore[union-attr]
            repo="octocat/hello-world",
            path="src",
            ref="main",
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.get_repo_tree")
        self.assertEqual(args["repo"], "octocat/hello-world")
        self.assertEqual(args["path"], "src")
        self.assertEqual(args["ref"], "main")
        self.assertNotIn("instruction", args)

    def test_github_list_user_repos_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_list_user_repos"].func(  # type: ignore[union-attr]
            username="octocat",
            visibility="public",
            limit=20,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.list_user_repos")
        self.assertEqual(args["username"], "octocat")
        self.assertEqual(args["visibility"], "public")
        self.assertEqual(args["limit"], 20)
        self.assertNotIn("instruction", args)

    def test_github_search_repos_omits_instruction_when_structured_args_exist(self) -> None:
        self.tools["github_search_repos"].func(  # type: ignore[union-attr]
            query="agent architecture",
            language="Python",
            limit=10,
            runtime=self.runtime,
        )

        tool_name, args = self.gateway.calls[-1]
        self.assertEqual(tool_name, "github.search_repos")
        self.assertEqual(args["query"], "agent architecture")
        self.assertEqual(args["language"], "Python")
        self.assertEqual(args["limit"], 10)
        self.assertNotIn("instruction", args)


if __name__ == "__main__":
    unittest.main()
