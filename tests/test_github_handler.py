from __future__ import annotations

import unittest
from dataclasses import dataclass

from agent.error_envelope import ErrorEnvelope
from agent.skills.github_handler import GitHubHandler
from agent.models import MiaChatRequest, MiaContext


@dataclass
class _DummyResult:
    ok: bool
    text: str
    payload: dict[str, object]
    error: ErrorEnvelope | None = None


class _DummyToolGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object], str]] = []

    def run_tool(self, tool_name: str, tool_args: dict[str, object], _context: MiaContext, request_text: str) -> _DummyResult:
        self.calls.append((tool_name, dict(tool_args), request_text))

        if tool_name == "github.get_repo":
            return _DummyResult(
                ok=True,
                text="Repo info",
                payload={"data": {"repo": tool_args.get("repo", "")}},
            )

        if tool_name == "github.get_file":
            if tool_args.get("path") != "README.md":
                raise AssertionError(f"unexpected file probe: {tool_args.get('path')}")
            return _DummyResult(
                ok=True,
                text="# README\n\nRepo overview.",
                payload={"data": {"path": tool_args.get("path", "")}},
            )

        if tool_name == "github.list_releases":
            return _DummyResult(
                ok=True,
                text="- v1.2.0\n- v1.1.0",
                payload={"data": {"items": [{"tag": "v1.2.0"}, {"tag": "v1.1.0"}]}},
            )

        if tool_name == "github.get_release":
            return _DummyResult(
                ok=True,
                text=f"Release {tool_args.get('releaseId') or tool_args.get('tag')}",
                payload={"data": {"releaseId": tool_args.get("releaseId", ""), "tag": tool_args.get("tag", "")}},
            )

        if tool_name == "github.list_issues":
            return _DummyResult(
                ok=True,
                text="- issue #1\n- issue #2",
                payload={"data": {"items": [{"number": 1}, {"number": 2}]}},
            )

        if tool_name == "github.get_issue":
            return _DummyResult(
                ok=True,
                text=f"Issue #{tool_args.get('number')}",
                payload={"data": {"number": tool_args.get("number", "")}},
            )

        raise AssertionError(f"unexpected tool call: {tool_name}")


class _DummyMemoryRepo:
    def __init__(self, recent_rows: list[dict[str, object]]) -> None:
        self._recent_rows = recent_rows

    def recent(self, chat_id: str, limit: int = 8) -> list[dict[str, object]]:
        return self._recent_rows[:limit]


class _DummyService:
    def __init__(self) -> None:
        self.tool_gateway = _DummyToolGateway()
        self.memory_repo = object()
        self.settings = object()
        self.document_followup_model = object()
        self.document_followup_fallback_model = object()


class GitHubHandlerReadmeOnlyTests(unittest.TestCase):
    def test_readme_only_analysis_does_not_probe_extra_files(self) -> None:
        service = _DummyService()
        handler = GitHubHandler(service)
        request = MiaChatRequest(chat_id="123", text="tóm tắt README đơn giản")
        context = MiaContext(chat_id="123", user_id="123", timezone="Asia/Ho_Chi_Minh", request_id="req-1")
        repo_context = {
            "repo": "jianchang512/pyvideotrans",
            "owner": "jianchang512",
            "repoName": "pyvideotrans",
            "repoUrl": "https://github.com/jianchang512/pyvideotrans",
        }

        sections, tools_called, code_search_hits, last_error = handler._collect_github_repo_analysis(
            request,
            context,
            repo_context,
            readme_only=True,
        )

        self.assertEqual(tools_called, ["github_get_repo", "github_get_file"])
        self.assertEqual([title for title, _ in sections], ["Repo info", "README"])
        self.assertEqual(code_search_hits, [])
        self.assertIsNone(last_error)
        self.assertEqual(
            [call[0] for call in service.tool_gateway.calls],
            ["github.get_repo", "github.get_file"],
        )
        self.assertEqual(service.tool_gateway.calls[1][1].get("path"), "README.md")

    def test_readme_only_analysis_propagates_last_error(self) -> None:
        class _ErrorToolGateway(_DummyToolGateway):
            def run_tool(self, tool_name: str, tool_args: dict[str, object], _context: MiaContext, request_text: str) -> _DummyResult:
                self.calls.append((tool_name, dict(tool_args), request_text))
                envelope = ErrorEnvelope.build(
                    code="tool_not_found",
                    category="not_found",
                    severity="warn",
                    message="github.get_file failed: HTTP 404",
                    user_message="Mình không tìm thấy README.md trong repo này.",
                    request_id="req-1",
                    chat_id="123",
                )
                return _DummyResult(
                    ok=False,
                    text=envelope.display_text(),
                    payload={"ok": False, "error": envelope.model_dump(mode="json")},
                    error=envelope,
                )

        service = _DummyService()
        service.tool_gateway = _ErrorToolGateway()
        handler = GitHubHandler(service)
        request = MiaChatRequest(chat_id="123", text="tóm tắt README đơn giản")
        context = MiaContext(chat_id="123", user_id="123", timezone="Asia/Ho_Chi_Minh", request_id="req-1")
        repo_context = {
            "repo": "jianchang512/pyvideotrans",
            "owner": "jianchang512",
            "repoName": "pyvideotrans",
            "repoUrl": "https://github.com/jianchang512/pyvideotrans",
        }

        sections, tools_called, code_search_hits, last_error = handler._collect_github_repo_analysis(
            request,
            context,
            repo_context,
            readme_only=True,
        )

        self.assertEqual(sections, [])
        self.assertEqual(code_search_hits, [])
        self.assertEqual(tools_called, [])
        self.assertIsNotNone(last_error)
        assert last_error is not None
        self.assertEqual(last_error.code, "tool_not_found")


class GitHubHandlerSelectedRepoFollowupTests(unittest.TestCase):
    def _build_handler(self, recent_rows: list[dict[str, object]]) -> GitHubHandler:
        service = _DummyService()
        service.memory_repo = _DummyMemoryRepo(recent_rows)
        return GitHubHandler(service)

    def test_selected_repo_release_latest_uses_release_tool(self) -> None:
        handler = self._build_handler(
            [
                {
                    "memory_type": "github_repo_selected",
                    "content": "Repo đã chọn: example/repo\nURL: https://github.com/example/repo",
                }
            ]
        )
        request = MiaChatRequest(chat_id="123", text="xem release mới nhất")
        context = MiaContext(chat_id="123", user_id="123", timezone="Asia/Ho_Chi_Minh", request_id="req-2")

        response = handler._try_github_selected_repo_followup(request, context)

        assert response is not None
        self.assertTrue(response.ok)
        self.assertEqual(response.tools_called, ["github_get_release"])
        self.assertEqual(response.final_text, "Release latest")
        self.assertEqual(handler.service.tool_gateway.calls[0][0], "github.get_release")
        self.assertEqual(handler.service.tool_gateway.calls[0][1].get("releaseId"), "latest")

    def test_selected_repo_issue_list_uses_issue_tool(self) -> None:
        handler = self._build_handler(
            [
                {
                    "memory_type": "github_repo_selected",
                    "content": "Repo đã chọn: example/repo\nURL: https://github.com/example/repo",
                }
            ]
        )
        request = MiaChatRequest(chat_id="123", text="xem issues open")
        context = MiaContext(chat_id="123", user_id="123", timezone="Asia/Ho_Chi_Minh", request_id="req-3")

        response = handler._try_github_selected_repo_followup(request, context)

        assert response is not None
        self.assertTrue(response.ok)
        self.assertEqual(response.tools_called, ["github_list_issues"])
        self.assertEqual(response.final_text, "- issue #1\n- issue #2")
        self.assertEqual(handler.service.tool_gateway.calls[0][0], "github.list_issues")
        self.assertEqual(handler.service.tool_gateway.calls[0][1].get("state"), "open")


if __name__ == "__main__":
    unittest.main()
