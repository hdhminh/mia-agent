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
    monkeypatch.delenv("MIA_CODE_GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)

    created = client.post("/projects/create", json={"project_name": "demo-code", "instruction": "tạo file demo"})
    assert created.status_code == 200
    project_id = created.json()["project"]["project_id"]
    workspace_path = Path(created.json()["project"]["workspace_path"])
    assert (workspace_path / "agent-output.txt").exists()

    diff = client.post("/projects/diff", json={"project_id": project_id})
    assert diff.status_code == 200
    assert "agent-output.txt" in diff.json()["diff"]
    assert project_id == "demo-code"


def test_opencode_create_project_reuses_existing_name(tmp_path, monkeypatch):
    fake_bin = tmp_path / "fake-opencode"
    _write_fake_opencode(fake_bin)

    monkeypatch.setenv("MIA_CODE_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("MIA_CODE_OPENCODE_BIN", str(fake_bin))
    monkeypatch.setenv("MIA_CODE_MODEL", "deepseek/deepseek-chat")
    monkeypatch.delenv("MIA_CODE_GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)

    created = client.post("/projects/create", json={"project_name": "demo-portfolio", "instruction": "tạo file demo"})
    assert created.status_code == 200
    first = created.json()["project"]
    assert first["project_id"] == "demo-portfolio"

    reused = client.post("/projects/create", json={"project_name": "demo-portfolio", "instruction": "thêm thay đổi mới"})
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
    monkeypatch.delenv("MIA_CODE_GATEWAY_TOKEN", raising=False)
    monkeypatch.delenv("MIA_CODE_RUNNER_TOKEN", raising=False)

    client = TestClient(app)
    imported = client.post("/projects/import", json={"source_path": str(repo)})
    assert imported.status_code == 200
    project_id = imported.json()["project"]["project_id"]
    workspace_path = Path(imported.json()["project"]["workspace_path"])
    (workspace_path / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    preview = client.post("/projects/apply", json={"project_id": project_id})
    assert preview.status_code == 200
    assert preview.json()["needs_confirmation"] is True

    applied = client.post("/projects/apply", json={"project_id": project_id, "confirmed": True})
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

    client = TestClient(app)
    response = client.post("/projects/import", json={"source_path": str(outside)})
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
