from __future__ import annotations

import hmac
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(title="Mia OpenCode Gateway", version="1.0.0")

PROJECT_META_DIR = ".mia-opencode"
PROJECT_META_FILE = "project.json"
DEFAULT_ALLOWED_COMMANDS = (
    "git status",
    "git diff",
    "git log",
    "git show",
    "git branch",
    "git rev-parse",
    "git ls-files",
    "git grep",
    "python",
    "python3",
    "pytest",
    "ruff",
    "mypy",
    "uv",
    "pip install",
    "pip3 install",
    "npm install",
    "npm run",
    "npm test",
    "pnpm install",
    "pnpm run",
    "pnpm test",
    "yarn install",
    "yarn run",
    "yarn test",
    "node",
    "go",
    "cargo",
    "make",
)
DEFAULT_ALLOWED_REGISTRIES = (
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "github.com",
    "api.github.com",
    "proxy.golang.org",
    "crates.io",
    "index.crates.io",
)


class CodeGatewayError(RuntimeError):
    """Operational error for the OpenCode gateway."""


@dataclass(frozen=True)
class ProjectRecord:
    project_id: str
    project_name: str
    workspace_path: str
    origin_type: str
    source_path: str
    session_id: str
    branch: str
    created_at: str
    updated_at: str
    title: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectRecord":
        return cls(
            project_id=str(payload.get("project_id") or ""),
            project_name=str(payload.get("project_name") or ""),
            workspace_path=str(payload.get("workspace_path") or ""),
            origin_type=str(payload.get("origin_type") or "workspace"),
            source_path=str(payload.get("source_path") or ""),
            session_id=str(payload.get("session_id") or ""),
            branch=str(payload.get("branch") or "main"),
            created_at=str(payload.get("created_at") or _now_iso()),
            updated_at=str(payload.get("updated_at") or _now_iso()),
            title=str(payload.get("title") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "workspace_path": self.workspace_path,
            "origin_type": self.origin_type,
            "source_path": self.source_path,
            "session_id": self.session_id,
            "branch": self.branch,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "title": self.title,
        }


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1)
    instruction: str = ""
    title: str = ""


class ImportProjectRequest(BaseModel):
    source_path: str = Field(min_length=1)
    project_name: str = ""
    instruction: str = ""
    title: str = ""


class WorkProjectRequest(BaseModel):
    project_id: str = ""
    instruction: str = Field(min_length=1)


class StatusProjectRequest(BaseModel):
    project_id: str = ""


class DiffProjectRequest(BaseModel):
    project_id: str = ""
    max_chars: int = 30000


class ApplyProjectRequest(BaseModel):
    project_id: str = ""
    confirmed: bool = False


class PublishProjectRequest(BaseModel):
    project_id: str = ""
    confirmed: bool = False
    mode: str = "push"
    branch: str = ""
    base: str = "main"
    title: str = ""
    body: str = ""


class TestProjectRequest(BaseModel):
    project_id: str = ""
    test_args: str = ""


class LintProjectRequest(BaseModel):
    project_id: str = ""
    tool: str = "auto"
    target: str = ""


class ReviewProjectRequest(BaseModel):
    project_id: str = ""
    scope: str = "diff"
    focus: str = ""


class OptimizeProjectRequest(BaseModel):
    project_id: str = ""
    focus: str = ""


class FixIssueRequest(BaseModel):
    project_id: str = ""
    repo: str = ""
    issue_number: str = ""
    issue_title: str = ""
    issue_body: str = ""
    base: str = "main"
    create_pr: bool = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require_auth(auth_header: str | None) -> None:
    token = os.getenv("MIA_CODE_GATEWAY_TOKEN", os.getenv("MIA_CODE_RUNNER_TOKEN", "")).strip()
    if not token:
        raise HTTPException(status_code=503, detail="Mia code gateway auth is not configured.")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    provided = auth_header.split(" ", 1)[1].strip()
    if not provided or not hmac.compare_digest(provided, token):
        raise HTTPException(status_code=401, detail="Invalid bearer token.")


def _workspace_root() -> Path:
    root = Path(os.getenv("MIA_CODE_WORKSPACE_ROOT", "/workspaces")).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _allowed_roots() -> list[Path]:
    raw = os.getenv("MIA_CODE_ALLOWED_ROOTS", "/host-projects")
    roots = []
    for part in raw.split(","):
        text = part.strip()
        if text:
            roots.append(Path(text).resolve())
    return roots


def _host_workspace_label() -> str:
    return os.getenv("MIA_CODE_HOST_WORKSPACE_ROOT", "/home/huynhminh/Projects/mia-workspaces").strip()


def _opencode_home() -> Path:
    root = Path(os.getenv("MIA_CODE_OPENCODE_HOME", "/tmp/mia-opencode-home")).resolve()
    (root / ".config" / "opencode").mkdir(parents=True, exist_ok=True)
    (root / ".local" / "share" / "opencode").mkdir(parents=True, exist_ok=True)
    return root


def _opencode_bin() -> str:
    return os.getenv("MIA_CODE_OPENCODE_BIN", "opencode").strip() or "opencode"


def _timeout_seconds() -> int:
    return max(30, int(float(os.getenv("MIA_CODE_TIMEOUT_SECONDS", os.getenv("MIA_CODE_RUNNER_TIMEOUT_SECONDS", "180")))))


def _code_model() -> str:
    raw = os.getenv("MIA_CODE_MODEL", "deepseek/deepseek-chat").strip()
    if "/" in raw:
        return raw
    return f"deepseek/{raw}" if raw else "deepseek/deepseek-chat"


def _code_model_parts() -> tuple[str, str]:
    raw = _code_model()
    if "/" in raw:
        provider, model = raw.split("/", 1)
        provider = provider.strip() or "deepseek"
        model = model.strip()
        if model:
            return provider, model
    return "deepseek", raw.strip() or "deepseek-chat"


def _code_model_cli() -> str:
    provider, model = _code_model_parts()
    return f"{provider}/{model}"


def _safe_slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower())
    normalized = normalized.strip("-")
    return normalized[:64] or "mia-workspace"


def _project_dir(project_id: str) -> Path:
    return _workspace_root() / project_id


def _project_meta_path(project_dir: Path) -> Path:
    return project_dir / PROJECT_META_DIR / PROJECT_META_FILE


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_opencode_files() -> None:
    home = _opencode_home()
    config_path = home / ".config" / "opencode" / "opencode.json"
    auth_path = home / ".local" / "share" / "opencode" / "auth.json"
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
    openrouter_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": _code_model(),
        "permission": {
            "*": "allow",
            "read": {
                "*": "allow",
                "*.env": "deny",
                "*.env.*": "deny",
                "*.env.example": "allow",
            },
            "edit": {
                "*": "allow",
                ".env": "deny",
                ".env.*": "deny",
            },
            "bash": {
                "*": "deny",
            },
            "webfetch": "deny",
            "websearch": "deny",
        },
        "agent": {
            "build": {
                "permission": {
                    "bash": {"*": "deny"},
                }
            }
        },
        "share": "disabled",
    }
    # Block bash prefixes that make trivial secret exfiltration easy (python -c "open('.env').read()").
    bash_excluded = {"python", "python3", "cat", "less", "more", "head", "tail", "sed", "awk"}
    for command in _allowed_command_prefixes():
        if command.strip() in bash_excluded:
            continue
        config["permission"]["bash"][f"{command}*"] = "allow"
        config["agent"]["build"]["permission"]["bash"][f"{command}*"] = "allow"
    if deepseek_base_url:
        config["provider"] = {
            "deepseek": {
                "options": {
                    "baseURL": deepseek_base_url,
                }
            }
        }
    if openrouter_base_url:
        providers = dict(config.get("provider") or {})
        providers["openrouter"] = {
            "options": {
                "baseURL": openrouter_base_url,
            }
        }
        config["provider"] = providers
    _write_json(config_path, config)
    auth_payload: dict[str, Any] = {}
    if deepseek_key:
        auth_payload["deepseek"] = {
            "type": "api",
            "key": deepseek_key,
        }
    if openrouter_key:
        auth_payload["openrouter"] = {
            "type": "api",
            "key": openrouter_key,
        }
    if auth_payload:
        _write_json(auth_path, auth_payload)


def _allowed_command_prefixes() -> tuple[str, ...]:
    raw = os.getenv("MIA_CODE_ALLOWED_COMMAND_PREFIXES", ",".join(DEFAULT_ALLOWED_COMMANDS))
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _allowed_registries() -> tuple[str, ...]:
    raw = os.getenv("MIA_CODE_ALLOWED_REGISTRIES", ",".join(DEFAULT_ALLOWED_REGISTRIES))
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _command_env() -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(_opencode_home())
    return env


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=_command_env(),
            text=True,
            capture_output=True,
            timeout=timeout or _timeout_seconds(),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CodeGatewayError(f"Command timed out: {' '.join(cmd)}") from exc
    except FileNotFoundError as exc:
        raise CodeGatewayError(f"Command not found on PATH: {cmd[0] if cmd else '?'}") from exc


def _run_checked(cmd: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    result = _run(cmd, cwd=cwd, timeout=timeout)
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise CodeGatewayError(message or f"Command failed: {' '.join(cmd)}")
    return result


def _detect_runner(project_dir: Path) -> tuple[str, list[str]]:
    if (project_dir / "pyproject.toml").exists() or (project_dir / "pytest.ini").exists() or (project_dir / "requirements.txt").exists():
        return "pytest", ["pytest", "-q"]
    if (project_dir / "package.json").exists():
        return "npm", ["npm", "test"]
    return "python", ["python", "-m", "pytest", "-q"]


def _run_tests(project_dir: Path, test_args: str = "") -> dict[str, Any]:
    runner, base_cmd = _detect_runner(project_dir)
    command = list(base_cmd)
    extra = [part for part in str(test_args or "").split() if part]
    if extra:
        command.extend(extra)
    result = _run(command, cwd=project_dir, timeout=min(_timeout_seconds(), 300))
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "runner": runner,
        "command": " ".join(command),
        "output": (result.stdout or "").strip()[-8000:],
        "stderr": (result.stderr or "").strip()[-2000:],
    }


def _run_lint(project_dir: Path, tool: str = "auto", target: str = "") -> dict[str, Any]:
    clean_tool = str(tool or "auto").strip().lower()
    targets = [str(target or "").strip()] if str(target or "").strip() else ["."]
    has_ruff = shutil.which("ruff") is not None
    has_mypy = shutil.which("mypy") is not None
    has_npm = shutil.which("npm") is not None and (project_dir / "package.json").exists()
    command: list[str] = []
    if clean_tool in {"auto", "ruff"} and has_ruff:
        command = ["ruff", "check"] + targets
    elif clean_tool in {"auto", "mypy"} and has_mypy:
        command = ["mypy"] + targets
    elif clean_tool in {"auto", "npm"} and has_npm:
        command = ["npm", "run", "lint"]
    else:
        return {
            "ok": False,
            "exit_code": 1,
            "runner": clean_tool,
            "command": "",
            "output": f"Không tìm thấy linter phù hợp cho tool '{clean_tool}' trong workspace.",
            "stderr": "",
        }
    result = _run(command, cwd=project_dir, timeout=min(_timeout_seconds(), 300))
    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "runner": clean_tool,
        "command": " ".join(command),
        "output": (result.stdout or "").strip()[-8000:],
        "stderr": (result.stderr or "").strip()[-2000:],
    }


def _build_review_prompt(focus: str, diff: str) -> str:
    lines = [
        "You are a senior software engineer reviewing code in this workspace.",
        "Rules:",
        "- Focus on real bugs, security issues, performance problems, and correctness.",
        "- Do NOT edit any files. Report findings only.",
        "- For each finding give: file, line if possible, severity, explanation, and a concrete suggestion.",
        "- Keep the report structured and concise.",
        "",
        "Task:",
        str(focus or "").strip() or "Review the current uncommitted changes for bugs, security, and performance.",
        "",
        "Current diff:",
        diff[:20000] or "(no diff)",
    ]
    return "\n".join(line for line in lines if line).strip()


def _build_fix_issue_prompt(issue_title: str, issue_body: str, issue_number: str) -> str:
    lines = [
        "You are a software engineer fixing a GitHub issue in this workspace.",
        "Rules:",
        "- Make the smallest effective change to fix the issue.",
        "- Run available tests or lint to verify your change if possible.",
        "- Do NOT read secrets or .env files.",
        "",
        "Issue to fix:",
        f"#{issue_number or '?'} {issue_title or ''}".strip(),
        (issue_body or "").strip(),
    ]
    return "\n".join(line for line in lines if line).strip()


def _ensure_git_repo(project_dir: Path) -> None:
    if (project_dir / ".git").exists():
        return
    _run_checked(["git", "init", "-b", "main"], cwd=project_dir)
    _run_checked(["git", "config", "user.email", "mia-opencode@example.local"], cwd=project_dir)
    _run_checked(["git", "config", "user.name", "Mia OpenCode"], cwd=project_dir)
    _run_checked(["git", "add", "-A"], cwd=project_dir)
    status = _run_checked(["git", "status", "--short"], cwd=project_dir)
    if status.stdout.strip():
        _run_checked(["git", "commit", "-m", "mia-opencode baseline"], cwd=project_dir)
    else:
        _run_checked(["git", "commit", "--allow-empty", "-m", "mia-opencode baseline"], cwd=project_dir)


def _load_project(project_id: str) -> ProjectRecord:
    if not project_id:
        projects = _list_projects()
        if len(projects) == 1:
            return projects[0]
        if not projects:
            raise CodeGatewayError("Chưa có project code nào. Hãy tạo mới hoặc import project trước.")
        raise CodeGatewayError("Có nhiều project code đang tồn tại. Cần chỉ rõ project_id.")
    project_dir = _project_dir(project_id)
    meta_path = _project_meta_path(project_dir)
    if not meta_path.exists():
        raise CodeGatewayError(f"Không tìm thấy project_id '{project_id}'.")
    return ProjectRecord.from_dict(_read_json(meta_path))


def _save_project(record: ProjectRecord) -> None:
    project_dir = Path(record.workspace_path)
    _write_json(_project_meta_path(project_dir), record.to_dict())


def _list_projects() -> list[ProjectRecord]:
    projects: list[ProjectRecord] = []
    for child in sorted(_workspace_root().iterdir()):
        meta_path = _project_meta_path(child)
        if meta_path.exists():
            projects.append(ProjectRecord.from_dict(_read_json(meta_path)))
    return projects


def _find_project_by_name(project_name: str) -> ProjectRecord | None:
    wanted_slug = _safe_slug(project_name)
    wanted_name = _normalize_name(project_name)
    for project in _list_projects():
        if _safe_slug(project.project_name) == wanted_slug:
            return project
        if _normalize_name(project.project_name) == wanted_name:
            return project
    return None


def _normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip()).casefold()


def _resolve_project_id(project_name: str) -> str:
    project_id = _safe_slug(project_name)
    existing_dir = _project_dir(project_id)
    if not existing_dir.exists():
        return project_id
    existing = _load_project(project_id)
    if _normalize_name(existing.project_name) == _normalize_name(project_name):
        return project_id
    raise CodeGatewayError(
        f"Tên project '{project_name}' bị trùng slug với project khác đang có: '{existing.project_name}'. "
        "Hãy đổi tên project rõ hơn thay vì tạo bản trùng."
    )


def _workspace_summary(record: ProjectRecord) -> dict[str, Any]:
    project_dir = Path(record.workspace_path)
    status = _run(["git", "status", "--short"], cwd=project_dir)
    changed_files = []
    for line in status.stdout.splitlines():
        line = line.strip()
        if len(line) >= 4:
            changed_files.append(line[3:].strip())
    return {
        "project_id": record.project_id,
        "project_name": record.project_name,
        "workspace_path": record.workspace_path,
        "workspace_host_root": _host_workspace_label(),
        "origin_type": record.origin_type,
        "source_path": record.source_path,
        "session_id": record.session_id,
        "branch": record.branch,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "changed_files": changed_files,
        "git_status": status.stdout.strip(),
    }


def _diff_text(project_dir: Path, *, max_chars: int) -> str:
    status_text = _run_checked(["git", "status", "--short"], cwd=project_dir).stdout.strip()
    diff_text = _run_checked(["git", "diff", "--binary"], cwd=project_dir).stdout.strip()
    parts = []
    if status_text:
        parts.append("Git status:\n" + status_text)
    if diff_text:
        parts.append(diff_text)
    text = "\n\n".join(parts).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "\n... [diff truncated]"
    return text


def _copy_project(src: Path, dest: Path) -> None:
    ignore_patterns = shutil.ignore_patterns(".git", ".env", ".env.*", "__pycache__", ".pytest_cache")
    shutil.copytree(src, dest, dirs_exist_ok=True, ignore=ignore_patterns)


def _validate_allowed_source(source_path: Path) -> None:
    allowed_roots = _allowed_roots()
    if not any(source_path == root or root in source_path.parents for root in allowed_roots):
        allowed = ", ".join(str(root) for root in allowed_roots)
        raise CodeGatewayError(f"Project local nằm ngoài vùng được phép import/apply. Allowed roots: {allowed}")


def _build_prompt(record: ProjectRecord, instruction: str) -> str:
    allowed_commands = ", ".join(_allowed_command_prefixes())
    allowed_registries = ", ".join(_allowed_registries())
    lines = [
        "You are OpenCode working for Mia inside a controlled coding workspace.",
        "Rules:",
        "- Stay strictly inside the current working directory.",
        "- Do not attempt to read secrets or .env files.",
        f"- Shell commands are restricted; prefer only these command prefixes when truly needed: {allowed_commands}.",
        f"- If installing dependencies is necessary, use package managers only and stay within trusted registries: {allowed_registries}.",
        "- Avoid destructive git operations.",
        "- Make the smallest effective set of changes, then stop.",
        "",
        "Task:",
        instruction.strip(),
    ]
    if record.origin_type == "imported" and record.source_path:
        lines.insert(
            2,
            f"- This workspace is a sandbox copy of an external project. Source path: {record.source_path}. Do not assume writes will sync back automatically.",
        )
    return "\n".join(lines).strip()


def _latest_session_id(project_dir: Path) -> str:
    result = _run_checked(
        [_opencode_bin(), "session", "list", "--format", "json", "-n", "1"],
        cwd=project_dir,
        timeout=60,
    )
    payload = json.loads(result.stdout or "[]")
    if isinstance(payload, list) and payload:
        latest = payload[0]
        if isinstance(latest, dict):
            return str(latest.get("id") or latest.get("sessionID") or "")
    return ""


def _run_opencode(record: ProjectRecord, instruction: str) -> tuple[str, str]:
    project_dir = Path(record.workspace_path)
    prompt = _build_prompt(record, instruction)
    session_id = record.session_id
    title = record.title or f"Mia: {record.project_name}"
    cmd = [
        _opencode_bin(),
        "run",
        "--auto",
        "--agent",
        "build",
        "--model",
        _code_model_cli(),
        "--dir",
        str(project_dir),
    ]
    if session_id:
        cmd.extend(["--session", session_id])
    else:
        cmd.extend(["--title", title])
    cmd.append(prompt)
    result = _run(cmd, cwd=project_dir, timeout=_timeout_seconds())
    if result.returncode != 0 and session_id:
        # The saved session may have been lost (e.g. opencode home reset after restart).
        # Retry once with a fresh session instead of failing the whole request.
        retry_cmd = [
            _opencode_bin(),
            "run",
            "--auto",
            "--agent",
            "build",
            "--model",
            _code_model_cli(),
            "--dir",
            str(project_dir),
            "--title",
            title,
            prompt,
        ]
        retry = _run(retry_cmd, cwd=project_dir, timeout=_timeout_seconds())
        if retry.returncode == 0:
            result = retry
            session_id = ""
    session_id = _latest_session_id(project_dir) or session_id
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "").strip()
        raise CodeGatewayError(message or "OpenCode không hoàn thành được tác vụ này.")
    output = (result.stdout or "").strip()
    return output, session_id


def _sync_back_to_source(record: ProjectRecord) -> list[str]:
    if record.origin_type != "imported" or not record.source_path:
        raise CodeGatewayError("Chỉ project import từ repo local mới có thể apply ngược về source.")
    source_path = Path(record.source_path).resolve()
    _validate_allowed_source(source_path)
    project_dir = Path(record.workspace_path)
    diff_names = _run_checked(["git", "diff", "--name-status"], cwd=project_dir).stdout.splitlines()
    touched: list[str] = []
    for line in diff_names:
        parts = line.split("\t")
        if not parts:
            continue
        status = parts[0]
        if status.startswith("R") and len(parts) >= 3:
            old_rel = parts[1]
            new_rel = parts[2]
            old_path = source_path / old_rel
            new_path = source_path / new_rel
            if old_path.exists():
                old_path.unlink()
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project_dir / new_rel, new_path)
            touched.extend([old_rel, new_rel])
            continue
        rel = parts[-1]
        source_file = source_path / rel
        workspace_file = project_dir / rel
        if status.startswith("D"):
            if source_file.exists():
                source_file.unlink()
            touched.append(rel)
            continue
        if workspace_file.is_file():
            source_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(workspace_file, source_file)
            touched.append(rel)
    return touched


def _commit_workspace_snapshot(project_dir: Path, message: str) -> None:
    _run_checked(["git", "add", "-A"], cwd=project_dir)
    status = _run_checked(["git", "status", "--short"], cwd=project_dir)
    if status.stdout.strip():
        _run_checked(["git", "commit", "-m", message], cwd=project_dir)


def _extract_github_remote(remote: str) -> tuple[str, str] | None:
    text = remote.strip()
    if not text:
        return None
    patterns = (
        r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)(?:\.git)?$",
        r"api\.github\.com/repos/(?P<owner>[^/]+)/(?P<repo>[^/.]+)$",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group("owner"), match.group("repo")
    return None


def _create_github_pr(owner: str, repo: str, branch: str, base: str, title: str, body: str) -> str:
    import httpx

    token = os.getenv("GITHUB_TOKEN", "").strip()
    if not token:
        raise CodeGatewayError("Thiếu GITHUB_TOKEN nên chưa thể tạo pull request.")
    response = httpx.post(
        f"https://api.github.com/repos/{owner}/{repo}/pulls",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        json={
            "title": title,
            "head": branch,
            "base": base,
            "body": body,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        raise CodeGatewayError(f"GitHub tạo PR lỗi HTTP {response.status_code}: {detail}")
    payload = response.json()
    return str(payload.get("html_url") or "")


@app.on_event("startup")
def _startup() -> None:
    _write_opencode_files()


@app.get("/health")
def health() -> dict[str, Any]:
    _write_opencode_files()
    return {
        "ok": True,
        "workspace_root": str(_workspace_root()),
        "model": _code_model(),
        "allowed_roots": [str(root) for root in _allowed_roots()],
    }


@app.post("/projects/create")
def create_project(
    body: CreateProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    _write_opencode_files()
    try:
        requested_name = body.project_name.strip()
        existing = _find_project_by_name(requested_name)
        reused_existing = existing is not None
        if existing is not None:
            record = existing
            project_id = existing.project_id
            project_dir = Path(existing.workspace_path)
        else:
            project_id = _resolve_project_id(requested_name)
            project_dir = _project_dir(project_id)
            project_dir.mkdir(parents=True, exist_ok=False)
            record = ProjectRecord(
                project_id=project_id,
                project_name=requested_name,
                workspace_path=str(project_dir),
                origin_type="workspace",
                source_path="",
                session_id="",
                branch="main",
                created_at=_now_iso(),
                updated_at=_now_iso(),
                title=body.title.strip(),
            )
            _save_project(record)
            _ensure_git_repo(project_dir)
        output = ""
        session_id = ""
        if body.instruction.strip():
            output, session_id = _run_opencode(record, body.instruction)
            record = ProjectRecord.from_dict({**record.to_dict(), "session_id": session_id, "updated_at": _now_iso()})
            _save_project(record)
        summary = _workspace_summary(record)
        host_path = f"{_host_workspace_label().rstrip('/')}/{project_id}"
        text = "\n".join(
            [
                (
                    f"Mia đã tiếp tục workspace code sẵn có: {record.project_name}"
                    if reused_existing
                    else f"Mia đã tạo workspace code mới: {record.project_name}"
                ),
                f"- project_id: {record.project_id}",
                f"- Workspace host path: {host_path}",
                f"- Model code: {_code_model()}",
                (
                    "- Mia tái sử dụng đúng project hiện có, không tạo bản trùng mới."
                    if reused_existing
                    else "- Ghi trực tiếp trong workspace riêng được bật."
                ),
                output.strip() if output.strip() else "",
            ]
        ).strip()
        return {"ok": True, "text": text, "project": summary, "output": output}
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/projects/import")
def import_project(
    body: ImportProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    _write_opencode_files()
    try:
        source_path = Path(body.source_path).resolve()
        if not source_path.exists() or not source_path.is_dir():
            raise HTTPException(status_code=404, detail="Source project path không tồn tại hoặc không phải thư mục.")
        _validate_allowed_source(source_path)
        project_name = body.project_name.strip() or source_path.name
        existing = _find_project_by_name(project_name)
        reused_existing = existing is not None
        if existing is not None:
            if existing.origin_type != "imported":
                raise CodeGatewayError(
                    f"Đã có workspace tên '{project_name}' nhưng đó là project nội bộ, không phải project import từ local."
                )
            if Path(existing.source_path).resolve() != source_path:
                raise CodeGatewayError(
                    f"Đã có project import tên '{project_name}' nhưng đang trỏ tới source khác: {existing.source_path}"
                )
            record = existing
            project_id = existing.project_id
            project_dir = Path(existing.workspace_path)
        else:
            project_id = _resolve_project_id(project_name)
            project_dir = _project_dir(project_id)
            _copy_project(source_path, project_dir)
            record = ProjectRecord(
                project_id=project_id,
                project_name=project_name,
                workspace_path=str(project_dir),
                origin_type="imported",
                source_path=str(source_path),
                session_id="",
                branch="main",
                created_at=_now_iso(),
                updated_at=_now_iso(),
                title=body.title.strip(),
            )
            _save_project(record)
            _ensure_git_repo(project_dir)
        output = ""
        session_id = ""
        if body.instruction.strip():
            output, session_id = _run_opencode(record, body.instruction)
            record = ProjectRecord.from_dict({**record.to_dict(), "session_id": session_id, "updated_at": _now_iso()})
            _save_project(record)
        summary = _workspace_summary(record)
        text = "\n".join(
            [
                (
                    f"Mia đã tiếp tục sandbox code đã import: {record.project_name}"
                    if reused_existing
                    else f"Mia đã import project vào sandbox code: {record.project_name}"
                ),
                f"- project_id: {record.project_id}",
                f"- Source path: {record.source_path}",
                f"- Workspace path: {record.workspace_path}",
                (
                    "- Mia tái sử dụng đúng project import hiện có, không tạo bản trùng mới."
                    if reused_existing
                    else "- Chưa ghi ngược về source cho tới khi anh xác nhận apply."
                ),
                output.strip() if output.strip() else "",
            ]
        ).strip()
        return {"ok": True, "text": text, "project": summary, "output": output}
    except HTTPException:
        raise
    except CodeGatewayError as exc:
        status = 403 if "Allowed roots" in str(exc) else 400
        raise HTTPException(status_code=status, detail=str(exc)) from exc


@app.post("/projects/work")
def work_project(
    body: WorkProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    _write_opencode_files()
    try:
        record = _load_project(body.project_id)
        output, session_id = _run_opencode(record, body.instruction)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    updated = ProjectRecord.from_dict({**record.to_dict(), "session_id": session_id, "updated_at": _now_iso()})
    _save_project(updated)
    summary = _workspace_summary(updated)
    text = "\n".join(
        [
            f"Mia đã tiếp tục project code: {updated.project_name}",
            f"- project_id: {updated.project_id}",
            f"- session_id: {updated.session_id or 'n/a'}",
            output.strip(),
        ]
    ).strip()
    return {"ok": True, "text": text, "project": summary, "output": output}


@app.post("/projects/status")
def project_status(
    body: StatusProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        if not body.project_id:
            projects = [_workspace_summary(project) for project in _list_projects()]
            return {"ok": True, "projects": projects, "text": json.dumps(projects, ensure_ascii=False, indent=2)}
        record = _load_project(body.project_id)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    summary = _workspace_summary(record)
    return {"ok": True, "project": summary, "text": json.dumps(summary, ensure_ascii=False, indent=2)}


@app.post("/projects/diff")
def project_diff(
    body: DiffProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        diff = _diff_text(Path(record.workspace_path), max_chars=max(1000, body.max_chars))
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not diff:
        diff = "(không có thay đổi so với baseline)"
    text = "\n".join(
        [
            f"Diff hiện tại của project {record.project_name}:",
            diff,
        ]
    )
    return {"ok": True, "project_id": record.project_id, "diff": diff, "text": text}


@app.post("/projects/apply")
def apply_project(
    body: ApplyProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        if not body.confirmed:
            return {
                "ok": True,
                "needs_confirmation": True,
                "text": f"Project {record.project_name} sẽ ghi ngược về source local. Cần confirmed=true để tiếp tục.",
            }
        touched = _sync_back_to_source(record)
        _commit_workspace_snapshot(Path(record.workspace_path), "mia-opencode synced to source")
        updated = ProjectRecord.from_dict({**record.to_dict(), "updated_at": _now_iso()})
        _save_project(updated)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    text = "\n".join(
        [
            f"Mia đã apply thay đổi của project {record.project_name} về source local.",
            f"- Source path: {record.source_path}",
            f"- File touched: {', '.join(touched) if touched else '(không có thay đổi)'}",
        ]
    )
    return {"ok": True, "text": text, "touched_files": touched}


@app.post("/projects/publish")
def publish_project(
    body: PublishProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        if not body.confirmed:
            return {
                "ok": True,
                "needs_confirmation": True,
                "text": f"Project {record.project_name} sẽ publish lên Git remote. Cần confirmed=true để tiếp tục.",
            }
        project_dir = Path(record.workspace_path)
        _run_checked(["git", "config", "user.email", "mia-opencode@example.local"], cwd=project_dir)
        _run_checked(["git", "config", "user.name", "Mia OpenCode"], cwd=project_dir)
        _run_checked(["git", "add", "-A"], cwd=project_dir)
        status = _run_checked(["git", "status", "--short"], cwd=project_dir)
        if status.stdout.strip():
            _run_checked(["git", "commit", "-m", body.title.strip() or "Mia OpenCode update"], cwd=project_dir)
        branch = body.branch.strip() or f"mia/{record.project_id}"
        _run_checked(["git", "checkout", "-B", branch], cwd=project_dir)
        remote = _run_checked(["git", "remote", "get-url", "origin"], cwd=project_dir).stdout.strip()
        _run_checked(["git", "push", "-u", "origin", branch], cwd=project_dir, timeout=max(60, _timeout_seconds()))
        pr_url = ""
        if body.mode.strip().lower() == "pr":
            parsed = _extract_github_remote(remote)
            if not parsed:
                raise CodeGatewayError("Remote hiện tại không phải GitHub nên chưa thể tạo pull request tự động.")
            owner, repo = parsed
            pr_url = _create_github_pr(
                owner=owner,
                repo=repo,
                branch=branch,
                base=body.base.strip() or "main",
                title=body.title.strip() or f"Mia OpenCode update for {record.project_name}",
                body=body.body.strip(),
            )
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    lines = [
        f"Mia đã publish project {record.project_name}.",
        f"- Branch: {branch}",
        f"- Remote: {remote}",
    ]
    if pr_url:
        lines.append(f"- Pull request: {pr_url}")
    return {"ok": True, "text": "\n".join(lines), "branch": branch, "remote": remote, "pull_request_url": pr_url}


@app.post("/projects/test")
def test_project(
    body: TestProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        result = _run_tests(Path(record.workspace_path), body.test_args)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    summary = (
        f"Mia đã chạy {result['command']} cho project {record.project_name}."
        f"\nKết quả: {'PASS' if result['ok'] else 'FAIL'} (exit {result['exit_code']})"
        f"\n{result['output']}"
    )
    if result.get("stderr"):
        summary += f"\nstderr:\n{result['stderr']}"
    return {"ok": True, "project_id": record.project_id, "text": summary, **result}


@app.post("/projects/lint")
def lint_project(
    body: LintProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        result = _run_lint(Path(record.workspace_path), body.tool, body.target)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    summary = (
        f"Mia đã chạy lint ({result['runner']}) cho project {record.project_name}: {result['command'] or 'n/a'}"
        f"\nKết quả: {'sạch' if result['ok'] else 'có vấn đề'} (exit {result['exit_code']})"
        f"\n{result['output']}"
    )
    return {"ok": True, "project_id": record.project_id, "text": summary, **result}


@app.post("/projects/review")
def review_project(
    body: ReviewProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        project_dir = Path(record.workspace_path)
        diff = _diff_text(project_dir, max_chars=20000)
        local_lint = _run_lint(project_dir, target="")
        prompt = _build_review_prompt(body.focus, diff)
        output, _session_id = _run_opencode(record, prompt)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    sections = []
    if diff:
        sections.append("Diff hiện tại:\n" + diff)
    lint_text = str(local_lint.get("output") or "(không có vấn đề)").strip()
    sections.append(f"Lint ({local_lint.get('command') or 'n/a'}):\n{lint_text}")
    sections.append("AI Review:\n" + (output or "").strip())
    return {
        "ok": True,
        "project_id": record.project_id,
        "text": "\n\n".join(sections),
        "review": output,
        "lint": local_lint,
        "diff": diff,
    }


@app.post("/projects/optimize")
def optimize_project(
    body: OptimizeProjectRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    try:
        record = _load_project(body.project_id)
        project_dir = Path(record.workspace_path)
        diff = _diff_text(project_dir, max_chars=15000)
        prompt_lines = [
            "You are a performance-focused software engineer optimizing this workspace.",
            "Rules:",
            "- Identify concrete performance and quality improvements.",
            "- Prefer proposing minimal, safe changes; do not rewrite working code.",
            "- Report findings with file, line if possible, expected impact, and a concrete suggestion.",
            "",
            "Focus:",
            str(body.focus or "").strip() or "Find performance and maintainability improvements in the current changes.",
            "",
            "Current diff:",
            diff[:15000] or "(no diff)",
        ]
        prompt = "\n".join(prompt_lines)
        output, _session_id = _run_opencode(record, prompt)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "ok": True,
        "project_id": record.project_id,
        "text": f"Mia đã phân tích tối ưu cho project {record.project_name}.\n\n{output}".strip(),
        "optimization": output,
    }


@app.post("/projects/fix-issue")
def fix_issue(
    body: FixIssueRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_auth(authorization)
    branch = ""
    try:
        record = _load_project(body.project_id)
        project_dir = Path(record.workspace_path)
        branch = f"mia/fix-{body.issue_number or 'issue'}-{record.project_id}"[:64].rstrip("-")
        _run_checked(["git", "checkout", "-B", branch], cwd=project_dir)
        prompt = _build_fix_issue_prompt(body.issue_title, body.issue_body, body.issue_number)
        output, session_id = _run_opencode(record, prompt)
        record = ProjectRecord.from_dict({**record.to_dict(), "session_id": session_id, "updated_at": _now_iso()})
        _save_project(record)
        _commit_workspace_snapshot(project_dir, f"Mia fix for #{body.issue_number or ''} {body.issue_title or ''}".strip())
        test_result = _run_tests(project_dir)
    except CodeGatewayError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    pr_url = ""
    if body.create_pr and test_result.get("ok"):
        remote = _run(["git", "remote", "get-url", "origin"], cwd=project_dir).stdout.strip()
        parsed = _extract_github_remote(body.repo) if "/" in str(body.repo or "") else _extract_github_remote(remote)
        if not parsed and "/" in str(body.repo or ""):
            parsed = _extract_github_remote(remote)
        if parsed:
            owner, repo_name = parsed
            title = f"[mia] {body.issue_title or f'Fix issue #{body.issue_number}'}".strip()
            pr_body = f"Fix for #{body.issue_number}\n\n{body.issue_body or ''}".strip()
            try:
                pr_url = _create_github_pr(owner, repo_name, branch, body.base or "main", title, pr_body)
            except CodeGatewayError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    lines = [
        f"Mia đã xử lý issue trên project {record.project_name}.",
        f"- Branch: {branch}",
        f"- Kết quả test: {'PASS' if test_result.get('ok') else 'FAIL'} (exit {test_result.get('exit_code')})",
        "",
        str(test_result.get("output") or "").strip(),
        "",
        str(output or "").strip(),
    ]
    if pr_url:
        lines.append(f"- Pull request: {pr_url}")
    return {
        "ok": True,
        "project_id": record.project_id,
        "branch": branch,
        "text": "\n".join(line for line in lines if line).strip(),
        "output": output,
        "test_result": test_result,
        "pull_request_url": pr_url,
    }
