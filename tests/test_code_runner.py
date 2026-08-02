from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = ROOT / "infra" / "opencode-gateway"
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from service.app import app  # noqa: E402


TOKEN = "test-gateway-token"


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def _write_fake_opencode(path: Path) -> None:
    script = """#!/usr/bin/env python3
import json
import pathlib
import sys

args = sys.argv[1:]
if args[:2] == ["session", "list"]:
    print(json.dumps([{"id": "sess-test-1", "title": "Fake session"}]))
    raise SystemExit(0)

if args and args[0] == "run":
    workdir = pathlib.Path(".")
    for index, value in enumerate(args):
        if value == "--dir" and index + 1 < len(args):
            workdir = pathlib.Path(args[index + 1])
            break
    target = workdir / "agent-output.txt"
    previous = target.read_text(encoding="utf-8") if target.exists() else ""
    target.write_text(previous + "updated by fake opencode\\n", encoding="utf-8")
    print("Fake OpenCode finished.")
    raise SystemExit(0)

print("unsupported", file=sys.stderr)
raise SystemExit(1)
"""
    path.write_text(script, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_opencode_create_project_and_diff(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("MIA_CODE_HOST_WORKSPACE_ROOT", "/home/huynhminh/Projects/mia-workspaces")
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)

    created = client.post("/projects/create", json={"project_name": "demo-code", "instruction": "tạo file demo"}, headers=_auth_headers())
    assert created.status_code == 200
    project_id = created.json()["project"]["project_id"]
    workspace_path = Path(created.json()["project"]["workspace_path"])
    assert (workspace_path / "agent-output.txt").exists()

    diff = client.post("/projects/diff", json={"project_id": project_id}, headers=_auth_headers())
    assert diff.status_code == 200
    assert "agent-output.txt" in diff.json()["diff"]
    assert project_id == "demo-code"


def test_opencode_create_project_reuses_existing_name(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)

    created = client.post("/projects/create", json={"project_name": "demo-portfolio", "instruction": "tạo file demo"}, headers=_auth_headers())
    assert created.status_code == 200
    first = created.json()["project"]
    assert first["project_id"] == "demo-portfolio"

    reused = client.post("/projects/create", json={"project_name": "demo-portfolio", "instruction": "thêm thay đổi mới"}, headers=_auth_headers())
    assert reused.status_code == 200
    second = reused.json()["project"]
    assert second["project_id"] == "demo-portfolio"
    assert "không tạo bản trùng mới" in reused.json()["text"]

    workspace_root = Path(tmp_path / "workspaces")
    projects = [path.name for path in workspace_root.iterdir() if path.is_dir()]
    assert projects == ["demo-portfolio"]


def test_opencode_import_and_apply_back_to_source(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    source_root = tmp_path / "Projects"
    repo = source_root / "demo"
    repo.mkdir(parents=True)
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.setenv("MIA_CODE_ALLOWED_ROOTS", str(source_root))
    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)
    imported = client.post("/projects/import", json={"source_path": str(repo)}, headers=_auth_headers())
    assert imported.status_code == 200
    project_id = imported.json()["project"]["project_id"]
    workspace_path = Path(imported.json()["project"]["workspace_path"])
    (workspace_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    preview = client.post("/projects/apply", json={"project_id": project_id}, headers=_auth_headers())
    assert preview.status_code == 200
    assert preview.json()["needs_confirmation"] is True

    applied = client.post("/projects/apply", json={"project_id": project_id, "confirmed": True}, headers=_auth_headers())
    assert applied.status_code == 200
    assert (repo / "app.py").read_text(encoding="utf-8") == "VALUE = 2\n"
    assert project_id == "demo"


def test_opencode_import_blocks_outside_allowed_roots(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("MIA_CODE_ALLOWED_ROOTS", str(tmp_path / "Projects"))
    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)

    client = TestClient(app)
    response = client.post("/projects/import", json={"source_path": str(outside)}, headers=_auth_headers())
    assert response.status_code == 403


def test_code_tools_use_default_project_id_when_missing(monkeypatch):
    from agent.skills.code_runner.tools import get_code_tools

    captured: list[tuple[str, dict[str, object]]] = []

    def fake_run(endpoint: str, payload: dict[str, object]) -> str:
        captured.append((endpoint, payload))
        return "ok"

    with patch("agent.skills.code_runner.tools._run", side_effect=fake_run):
        tools = {tool.name: tool for tool in get_code_tools(default_project_id="demo-coffee")}
        tools["code_work_on_project"].func(project_id="", instruction="thêm about")
        tools["code_project_diff"].func(project_id="", max_chars=1234)
        tools["code_publish_project"].func(project_id="", confirmed=False)

    assert captured[0] == ("projects/work", {"project_id": "demo-coffee", "instruction": "thêm about"})
    assert captured[1] == ("projects/diff", {"project_id": "demo-coffee", "max_chars": 1234})
    assert captured[2][0] == "projects/publish"
    assert captured[2][1]["project_id"] == "demo-coffee"


def test_code_import_translates_host_projects_path(monkeypatch):
    from agent.skills.code_runner.tools import get_code_tools

    captured = []

    def fake_run(endpoint: str, payload: dict):
        captured.append((endpoint, payload))
        return {"text": "ok"}

    monkeypatch.setenv("MIA_CODE_HOST_PROJECTS_ROOT", "/home/huynhminh/Projects")
    monkeypatch.setenv("MIA_CODE_CONTAINER_PROJECTS_ROOT", "/host-projects")

    with patch("agent.skills.code_runner.tools._run", side_effect=fake_run):
        tools = {tool.name: tool for tool in get_code_tools()}
        tools["code_import_existing_project"].func(
            source_path="/home/huynhminh/Projects/mia-agent",
            project_name="mia-agent",
        )

    assert captured[0] == (
        "projects/import",
        {
            "source_path": "/host-projects/mia-agent",
            "project_name": "mia-agent",
            "instruction": "",
            "title": "",
        },
    )


def test_new_dev_tools_map_to_correct_endpoints(monkeypatch):
    from agent.skills.code_runner.tools import get_code_tools

    captured: list[tuple[str, dict[str, object]]] = []

    def fake_run(endpoint: str, payload: dict[str, object]) -> str:
        captured.append((endpoint, payload))
        return "ok"

    with patch("agent.skills.code_runner.tools._run", side_effect=fake_run):
        tools = {tool.name: tool for tool in get_code_tools(default_project_id="demo-core")}
        tools["code_review_project"].func(project_id="", focus="bugs")
        tools["code_optimize_project"].func(project_id="", focus="perf")
        tools["code_run_test"].func(project_id="", test_args="-x")
        tools["code_run_lint"].func(project_id="", tool="ruff")
        tools["code_fix_from_issue"].func(
            project_id="",
            repo="octocat/hello-world",
            issue_number="7",
            issue_title="Fix crash",
            issue_body="It crashes",
            create_pr=True,
        )

    assert captured[0] == ("projects/review", {"project_id": "demo-core", "scope": "diff", "focus": "bugs"})
    assert captured[1] == ("projects/optimize", {"project_id": "demo-core", "focus": "perf"})
    assert captured[2] == ("projects/test", {"project_id": "demo-core", "test_args": "-x"})
    assert captured[3] == ("projects/lint", {"project_id": "demo-core", "tool": "ruff", "target": ""})
    fix_payload = captured[4][1]
    assert captured[4][0] == "projects/fix-issue"
    assert fix_payload["project_id"] == "demo-core"
    assert fix_payload["issue_number"] == "7"
    assert fix_payload["create_pr"] is True


def test_projects_test_and_lint_endpoints_respond(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)
    created = client.post("/projects/create", json={"project_name": "demo-lint", "instruction": ""}, headers=_auth_headers())
    assert created.status_code == 200
    project_id = created.json()["project"]["project_id"]

    test_resp = client.post("/projects/test", json={"project_id": project_id}, headers=_auth_headers())
    assert test_resp.status_code == 200
    body = test_resp.json()
    assert "exit_code" in body
    assert "output" in body

    lint_resp = client.post("/projects/lint", json={"project_id": project_id, "tool": "ruff"}, headers=_auth_headers())
    assert lint_resp.status_code == 200
    lint_body = lint_resp.json()
    assert "output" in lint_body


def test_projects_review_endpoint_uses_fake_opencode(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)
    created = client.post("/projects/create", json={"project_name": "demo-review", "instruction": "tao file demo"}, headers=_auth_headers())
    assert created.status_code == 200
    project_id = created.json()["project"]["project_id"]

    review = client.post("/projects/review", json={"project_id": project_id, "focus": "bugs"}, headers=_auth_headers())
    assert review.status_code == 200
    assert review.json()["project_id"] == project_id
    assert "AI Review" in review.json()["text"]


def test_gateway_auth_fails_closed_without_token(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)
    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.delenv("MIA_CODE_GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)
    response = client.post("/projects/create", json={"project_name": "demo-noauth", "instruction": ""})
    assert response.status_code == 503


def test_gateway_auth_rejects_wrong_token(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)
    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_GATEWAY_TOKEN", TOKEN)

    client = TestClient(app)
    response = client.post(
        "/projects/create",
        json={"project_name": "demo-badauth", "instruction": ""},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert response.status_code == 401


class _FakeApprovalRepo:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create_pending_action(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"id": 1, "summary": "code action", **kwargs}

    def claim_pending_action(self, **kwargs: object) -> dict[str, object]:
        return {
            "id": 1,
            "gateway_name": "code.publish_project",
            "args": {"endpoint": "projects/publish", "payload": {"project_id": "p", "confirmed": True}},
        }

    def mark_pending_action_status(self, *args: object, **kwargs: object) -> None:
        pass


class _FakeCodeClient:
    def __init__(self) -> None:
        self.called: tuple[str, dict] | None = None

    def request(self, endpoint: str, payload: dict) -> dict:
        self.called = (endpoint, payload)
        return {"ok": True, "text": "published", "data": {}}


def test_code_dangerous_tool_requires_approval(monkeypatch):
    from types import SimpleNamespace
    from agent.skills.code_runner.tools import get_code_tools

    fake_repo = _FakeApprovalRepo()
    tool_gateway = SimpleNamespace(approval_repo=fake_repo)
    captured: list[tuple[str, dict]] = []

    def fake_run(endpoint: str, payload: dict) -> str:
        captured.append((endpoint, payload))
        return "executed"

    class FakeContext:
        chat_id = "chat-1"
        user_id = "user-1"
        request_id = "req-1"

    class FakeRuntime:
        context = FakeContext()

    with patch("agent.skills.code_runner.tools._run", side_effect=fake_run):
        tools = {tool.name: tool for tool in get_code_tools(default_project_id="demo-core", tool_gateway=tool_gateway)}
        result = tools["code_apply_to_existing_project"].func(project_id="", confirmed=False, runtime=FakeRuntime())

    assert captured == []
    assert fake_repo.calls
    call = fake_repo.calls[0]
    assert call["gateway_name"] == "code.apply_to_existing_project"
    assert call["args"]["endpoint"] == "projects/apply"
    assert call["args"]["payload"]["confirmed"] is True
    assert "approval_required" in result or "xác nhận" in result or "confirm" in result


def test_code_fix_issue_without_pr_executes_directly(monkeypatch):
    from types import SimpleNamespace
    from agent.skills.code_runner.tools import get_code_tools

    tool_gateway = SimpleNamespace(approval_repo=_FakeApprovalRepo())
    captured: list[tuple[str, dict]] = []

    def fake_run(endpoint: str, payload: dict) -> str:
        captured.append((endpoint, payload))
        return "fixed"

    with patch("agent.skills.code_runner.tools._run", side_effect=fake_run):
        tools = {tool.name: tool for tool in get_code_tools(default_project_id="demo-core", tool_gateway=tool_gateway)}
        result = tools["code_fix_from_issue"].func(project_id="", issue_number="3", issue_title="T", create_pr=False)

    assert captured == [("projects/fix-issue", {"project_id": "demo-core", "repo": "", "issue_number": "3", "issue_title": "T", "issue_body": "", "base": "main", "create_pr": False})]
    assert result == "fixed"


def test_run_pending_action_dispatches_code_tool():
    from types import SimpleNamespace
    from agent.execution_client import N8nToolGatewayClient

    fake_repo = _FakeApprovalRepo()
    code_client = _FakeCodeClient()
    gw = N8nToolGatewayClient(
        url="http://n8n",
        token="t",
        timeout_seconds=10,
        approval_repo=fake_repo,
        code_runner_client=code_client,
    )
    context = SimpleNamespace(chat_id="c", user_id="u", request_id="r", timezone="UTC")
    result = gw.run_pending_action({"id": 1, "gateway_name": "code.publish_project", "args": {}}, context)
    assert code_client.called == ("projects/publish", {"project_id": "p", "confirmed": True})
    assert result.ok
    assert result.text == "published"
