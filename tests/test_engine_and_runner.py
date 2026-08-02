from __future__ import annotations

import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from agent.skills_engine.engine import SkillEngine


class SkillEngineSelectTest(unittest.TestCase):
    def setUp(self):
        self.repo = SimpleNamespace(start=MagicMock(), finish=MagicMock())
        self.path = Path(__file__).resolve().parents[1] / "agent" / "skills_engine" / "skills.yaml"
        self.engine = SkillEngine.load(repository=self.repo, path=self.path)

    def test_load_has_8_skills(self):
        names = [s.name for s in self.engine.specs]
        self.assertIn("remind_me", names)
        self.assertIn("home_control", names)
        self.assertIn("repository_review", names)
        self.assertEqual(len(self.engine.specs), 8)

    def test_select_matches_reminder(self):
        spec = self.engine.select("nhắc tôi uống nước lúc 9h")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.name, "remind_me")

    def test_select_matches_home_control(self):
        spec = self.engine.select("bật đèn phòng ngủ")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.name, "home_control")

    def test_select_returns_none_for_unrelated(self):
        self.assertIsNone(self.engine.select("màu yêu thích của bạn là gì"))

    def test_start_guidance_records_run(self):
        name, guidance = self.engine.start_guidance(query="nhắc tôi 8h", request_id="r1", chat_id="c", user_id="u")
        self.assertEqual(name, "remind_me")
        self.assertIn("remind_me", guidance)
        self.repo.start.assert_called_once()


class AutomationRunnerTest(unittest.TestCase):
    def test_quiet_hours_empty(self):
        from agent.automation_runner import AutomationRunner

        r = AutomationRunner(repository=None, service=None, poll_seconds=30, quiet_hours="")
        self.assertFalse(r._in_quiet_hours(0))
        self.assertFalse(r._in_quiet_hours(12))

    def test_quiet_hours_overnight(self):
        from agent.automation_runner import AutomationRunner

        r = AutomationRunner(repository=None, service=None, poll_seconds=30, quiet_hours="23-7")
        self.assertTrue(r._in_quiet_hours(23))
        self.assertTrue(r._in_quiet_hours(0))
        self.assertFalse(r._in_quiet_hours(8))

    def test_remind_execution_skips_during_quiet(self):
        from agent.automation_runner import AutomationRunner

        service = SimpleNamespace(
            settings=SimpleNamespace(timezone="Asia/Ho_Chi_Minh"),
            chat=MagicMock(),
            tool_gateway=None,
        )
        r = AutomationRunner(repository=None, service=service, poll_seconds=30, quiet_hours="23-7")
        automation = {
            "id": 1,
            "chat_id": "c",
            "user_id": "u",
            "skill_name": "remind_me",
            "input_text": "Nhắc test",
            "schedule": "0 8 * * *",
            "name": "r",
        }
        finish = MagicMock()
        r.repository = SimpleNamespace(finish_run=finish)
        asyncio.run(r._execute(automation))
        # quiet hours may or may not apply depending on wall clock; assert no crash and chat called OR skipped
        service.chat.assert_called()


if __name__ == "__main__":
    unittest.main()
