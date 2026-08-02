from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from agent.skills.github_write import get_github_write_tools
from agent.skills.smarthome import get_smarthome_tools
from agent.skills.google_maps import get_google_maps_tools


def _fake_runtime(**overrides):
    context = SimpleNamespace(
        chat_id=overrides.get("chat_id", "chat-1"),
        user_id=overrides.get("user_id", "user-1"),
        request_id=overrides.get("request_id", "req-1"),
        timezone="Asia/Ho_Chi_Minh",
    )
    return SimpleNamespace(context=context)


class _Gateway:
    def __init__(self):
        self.calls = []

    def run_tool(self, gateway_name, args, context, **kwargs):
        self.calls.append((gateway_name, args))
        return SimpleNamespace(ok=True, text="ok", payload={})


class GitHubWritePayloadTest(unittest.TestCase):
    def setUp(self):
        self.gw = _Gateway()
        self.tools = {t.name: t for t in get_github_write_tools(self.gw)}

    def _call(self, name, runtime, **kwargs):
        return self.tools[name].func(runtime=runtime, **kwargs)

    def test_create_issue_payload(self):
        self._call("github_create_issue", _fake_runtime(), repo="octo/repo", title="Bug", body="desc")
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "github.create_issue")
        self.assertEqual(args["repo"], "octo/repo")
        self.assertEqual(args["title"], "Bug")
        self.assertEqual(args["body"], "desc")

    def test_create_pull_request_defaults_to_draft(self):
        self._call("github_create_pull_request", _fake_runtime(), repo="octo/repo", title="PR", head="feat/x", base="main")
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "github.create_pull_request")
        self.assertEqual(args["draft"], True)

    def test_update_file_base64(self):
        self._call("github_update_file", _fake_runtime(), repo="octo/repo", path="a.py", content_base64="cHJpbnQoKQ==", message="m", branch="main")
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "github.update_file")
        self.assertEqual(args["content"], "cHJpbnQoKQ==")

    def test_all_write_tools_are_dangerous(self):
        from agent.approval import should_require_confirmation
        # list_workflow_runs is read-only; the rest are write actions
        write_names = [n for n in self.tools if n != "github_list_workflow_runs"]
        for name in write_names:
            self.assertTrue(should_require_confirmation(name.replace("github_", "github."), {}, ""), f"{name} should require approval")


class SmarthomePayloadTest(unittest.TestCase):
    def setUp(self):
        self.gw = _Gateway()
        self.tools = {t.name: t for t in get_smarthome_tools(self.gw)}

    def test_turn_on_payload(self):
        self.tools["smarthome_turn_on"].func(runtime=_fake_runtime(), target="đèn phòng ngủ")
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "smarthome.turn_on")

    def test_set_light_has_instruction_fallback(self):
        self.tools["smarthome_set_light"].func(runtime=_fake_runtime(), target="đèn", brightness_pct=80)
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "smarthome.set_light")
        # structured value present -> no instruction key
        self.assertNotIn("instruction", args)

    def test_help_uses_empty_payload(self):
        self.tools["smarthome_help"].func(runtime=_fake_runtime())
        self.assertEqual(self.gw.calls[-1][0], "smarthome.help")


class GoogleMapsPayloadTest(unittest.TestCase):
    def setUp(self):
        self.gw = _Gateway()
        self.tools = {t.name: t for t in get_google_maps_tools(self.gw)}

    def test_geocode_payload(self):
        self.tools["maps_geocode"].func(runtime=_fake_runtime(), address="Hanoi")
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "maps.geocode")

    def test_search_place_has_limit(self):
        self.tools["maps_search_place"].func(runtime=_fake_runtime(), query="cà phê", max_results=5)
        gw_name, args = self.gw.calls[-1]
        self.assertEqual(gw_name, "maps.search_place")
        self.assertEqual(args.get("maxResults"), 5)


if __name__ == "__main__":
    unittest.main()
