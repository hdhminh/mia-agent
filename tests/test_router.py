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

    def test_project_memory_question_does_not_route_to_code(self):
        decision = route_request("mật danh dự án trong bài test smoke là gì?")
        self.assertEqual(decision.domain, "general")
        self.assertEqual(decision.agent_key, "general")

    def test_generic_project_question_does_not_route_to_code(self):
        decision = route_request("demo-coffee là project gì vậy?")
        self.assertEqual(decision.domain, "general")
        self.assertEqual(decision.agent_key, "general")

    def test_drive_folder_project_request_does_not_route_to_code(self):
        decision = route_request("tạo folder dự án mới")
        self.assertEqual(decision.domain, "workspace")
        self.assertEqual(decision.agent_key, "workspace")
        self.assertEqual(decision.hint_tool, "drive_create_folder")

    def test_sheet_and_drive_multi_intent_does_not_route_to_code(self):
        decision = route_request("xem file drive gần đây rồi thêm dòng vào sheet doanh thu")
        self.assertEqual(decision.domain, "workspace")
        self.assertEqual(decision.agent_key, "google_full")
        self.assertEqual(decision.hint_tool, "drive_create_file")

    def test_explicit_code_folder_creation_still_routes_to_code(self):
        decision = route_request("tạo folder mới trong Projects để code landing page html css")
        self.assertEqual(decision.domain, "code")
        self.assertEqual(decision.agent_key, "code")
        self.assertEqual(decision.hint_tool, "code_create_project")

    def test_code_workspace_status_routes_to_code_status(self):
        decision = route_request("kiểm tra workspace code hiện có")
        self.assertEqual(decision.domain, "code")
        self.assertEqual(decision.agent_key, "code")
        self.assertEqual(decision.hint_tool, "code_project_status")

if __name__ == "__main__":
    unittest.main()
