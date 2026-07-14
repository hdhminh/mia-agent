from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from agent.approval import is_cancellation_text, is_confirmation_text, should_require_confirmation
from agent.automation import compute_next_run
from agent.brain.capability_broker import CapabilityBroker
from agent.brain.planner import infer_request_profile
from agent.execution_journal import build_idempotency_key, canonical_args_hash
from agent.mcp_adapter import MCPAdapter
from agent.rate_limit import SlidingWindowRateLimiter
from agent.service import MiaAgentService
from agent.skills_engine.engine import SkillEngine, SkillSpec
from agent.tool_specs import ToolCatalog
from agent.models import MiaChatRequest


ROOT = Path(__file__).resolve().parents[1]


class PlatformSafetyTests(unittest.TestCase):
    def test_confirmation_requires_exact_positive_response(self) -> None:
        for value in ("xác nhận", "OK!", "confirm 42", "làm đi"):
            self.assertTrue(is_confirmation_text(value), value)
        for value in ("không xác nhận", "ok nhưng đừng làm", "not ok", "đây có ok không"):
            self.assertFalse(is_confirmation_text(value), value)

    def test_cancellation_is_exact_and_write_tools_require_approval(self) -> None:
        self.assertTrue(is_cancellation_text("Hủy!"))
        self.assertFalse(is_cancellation_text("hủy lịch ngày mai"))
        self.assertTrue(should_require_confirmation("github.update_file"))
        self.assertTrue(should_require_confirmation("automation.create"))
        self.assertTrue(should_require_confirmation("gmail.draft_email"))
        self.assertTrue(should_require_confirmation("drive.create_file"))
        self.assertTrue(should_require_confirmation("shortlink.create"))
        self.assertTrue(should_require_confirmation("code.apply_to_local"))
        self.assertTrue(should_require_confirmation("code.create_pull_request"))
        self.assertFalse(should_require_confirmation("contacts.search"))

    def test_idempotency_is_stable_and_sensitive_to_arguments(self) -> None:
        self.assertEqual(canonical_args_hash({"b": 2, "a": 1}), canonical_args_hash({"a": 1, "b": 2}))
        first = build_idempotency_key(user_id="u", request_id="r", tool_name="tasks.create", args={"title": "A"})
        second = build_idempotency_key(user_id="u", request_id="r", tool_name="tasks.create", args={"title": "B"})
        self.assertNotEqual(first, second)

    def test_rate_limiter_rejects_after_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
        self.assertEqual(limiter.allow("user")[0], True)
        self.assertEqual(limiter.allow("user")[0], True)
        allowed, retry_after = limiter.allow("user")
        self.assertFalse(allowed)
        self.assertGreaterEqual(retry_after, 1)


class PlatformCapabilityTests(unittest.TestCase):
    def test_catalog_and_broker_keep_memory_and_hint(self) -> None:
        catalog = ToolCatalog.load()
        self.assertGreaterEqual(len(catalog.specs), 100)
        broker = CapabilityBroker(catalog)
        selected = broker.select_tool_names(
            query="create an issue in github",
            domain="github",
            available=["memory_search", "github_get_repo", "github_create_issue", "weather_current"],
            hint_tool="github_create_issue",
            limit=3,
        )
        self.assertIn("memory_search", selected)
        self.assertIn("github_create_issue", selected)

    def test_skill_selector_matches_reusable_workflow(self) -> None:
        class Repository:
            def start(self, **_: object) -> dict[str, object]:
                return {}

        engine = SkillEngine(
            repository=Repository(),  # type: ignore[arg-type]
            specs=[
                SkillSpec(
                    name="daily_briefing",
                    description="Daily briefing",
                    triggers=("daily briefing", "điểm tin sáng"),
                    required_capabilities=("calendar",),
                    steps=("Read calendar",),
                    approval_points=(),
                    success_criteria=("Brief delivered",),
                )
            ],
        )
        self.assertEqual(engine.select("Cho mình daily briefing").name, "daily_briefing")  # type: ignore[union-attr]

    def test_mcp_requires_https_and_read_only_allowlist(self) -> None:
        with self.assertRaises(ValueError):
            MCPAdapter(servers_json=json.dumps({"unsafe": {"url": "http://localhost:9000"}}))
        adapter = MCPAdapter(
            servers_json=json.dumps(
                {"docs": {"url": "https://mcp.example.com", "read_only_tools": ["search"]}}
            )
        )
        with self.assertRaises(PermissionError):
            adapter.call_read_only_tool("docs", "delete", {})

    def test_cron_schedule_computes_next_run(self) -> None:
        base = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
        next_run = compute_next_run("0 8 * * *", after=base)
        self.assertEqual((next_run.hour, next_run.minute), (8, 0))
        with self.assertRaises(ValueError):
            compute_next_run("tomorrow morning", after=base)

    def test_active_code_project_followup_routes_to_code(self) -> None:
        profile = infer_request_profile(
            "thêm section about nữa đi",
            metadata={
                "active_code_project": {
                    "project_id": "demo-coffee",
                    "project_name": "demo-coffee",
                }
            },
        )
        self.assertEqual(profile.domain, "code")
        self.assertEqual(profile.hint_tool, "code_work_on_project")

    def test_service_resolves_named_code_project_from_request_text(self) -> None:
        service = object.__new__(MiaAgentService)
        service.settings = SimpleNamespace(code_enabled=True)
        service.code_runner_client = SimpleNamespace(
            list_projects=lambda: [
                {"project_id": "demo-coffee", "project_name": "demo-coffee"},
                {"project_id": "demo-portfolio", "project_name": "demo-portfolio"},
            ]
        )
        request = MiaChatRequest(chat_id="1", text="thêm section about vào demo-coffee", metadata={})
        active = service._resolve_active_code_project(request)
        self.assertEqual(active.get("project_id"), "demo-coffee")


class PlatformWorkflowContractTests(unittest.TestCase):
    def test_gateway_is_fail_closed_and_routes_new_domains(self) -> None:
        path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        raw = path.read_text(encoding="utf-8")
        for marker in (
            "Tool gateway authentication is not configured",
            "Sub-workflow: Media Master",
            "tasks.list",
            "contacts.search",
            "automation.create",
            "github.create_pull_request",
        ):
            self.assertIn(marker, raw)

    def test_new_workflows_have_names(self) -> None:
        paths = (
            ROOT / "execution/integrations/google/tasks/workflow_sub_google_tasks_master.json",
            ROOT / "execution/integrations/google/contacts/workflow_sub_google_contacts_master.json",
            ROOT / "execution/integrations/automation/workflow_sub_automation_master.json",
        )
        for path in paths:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(payload.get("name"), path.name)
            self.assertTrue(payload.get("nodes"), path.name)


if __name__ == "__main__":
    unittest.main()
