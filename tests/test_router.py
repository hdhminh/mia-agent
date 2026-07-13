import unittest
from agent.brain.router import route_request, choose_agent_key
from agent.brain.parsers.common import RequestProfile

class TestRouter(unittest.TestCase):
    def test_choose_agent_key_simple(self):
        # Test routing for news request (general)
        profile = RequestProfile(domain="general", hint_tool="news_get", direct_confident=True, reason="explicit news request")
        self.assertEqual(choose_agent_key(profile, "tin tức hôm nay"), "general")

        # Test routing for calendar
        profile_cal = RequestProfile(domain="calendar", hint_tool="calendar_list_today", direct_confident=True, reason="calendar request")
        self.assertEqual(choose_agent_key(profile_cal, "lịch hôm nay"), "calendar")

        # Test routing for github
        profile_git = RequestProfile(domain="github", hint_tool="github_list_user_repos", direct_confident=True, reason="github request")
        self.assertEqual(choose_agent_key(profile_git, "github repos"), "github")

    def test_route_request_weather(self):
        # Weather is a deterministic direct tool
        decision = route_request("thời tiết hôm nay thế nào")
        self.assertEqual(decision.hint_tool, "weather_get")
        self.assertEqual(decision.route_type, "direct_deterministic")
        self.assertTrue(decision.use_direct)

    def test_route_request_multi_step(self):
        # Multi-step requests should go to agentic route
        decision = route_request("xem lịch của tôi xong thì gửi mail cho sếp")
        self.assertEqual(decision.route_type, "agentic_multistep")
        self.assertEqual(decision.agent_key, "google_full")

    def test_route_request_code_agent(self):
        decision = route_request("sửa bug trong repo mia-agent rồi chạy test")
        self.assertEqual(decision.domain, "code")
        self.assertEqual(decision.agent_key, "code")
        self.assertEqual(decision.hint_tool, "code_work_on_project")

if __name__ == "__main__":
    unittest.main()
