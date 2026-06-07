from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LANGCHAIN_ROOT = ROOT / "langchain_core"
if str(LANGCHAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(LANGCHAIN_ROOT))

from mia_core.request_parser import build_direct_tool_args
from mia_core.router import route_request


class TestRequestParserUrlInstructions(unittest.TestCase):
    def test_summarize_url_instruction_drops_url(self) -> None:
        url = "https://example.com/article-2"
        args = build_direct_tool_args("summarize_url", f"tóm tắt link này {url}", {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "tóm tắt link này")
        self.assertEqual(args["text"], "tóm tắt link này")
        self.assertEqual(args["prompt"], "tóm tắt link này")

    def test_ask_url_instruction_keeps_question_without_url(self) -> None:
        url = "https://example.com/article-3"
        args = build_direct_tool_args("ask_url", f"{url} link này nói gì về học phí?", {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "link này nói gì về học phí?")
        self.assertEqual(args["question"], "link này nói gì về học phí?")
        self.assertEqual(args["prompt"], "link này nói gì về học phí?")

    def test_ask_url_with_only_url_falls_back_to_generic_question(self) -> None:
        url = "https://example.com/article-4"
        args = build_direct_tool_args("ask_url", url, {"url": url})

        self.assertEqual(args["url"], url)
        self.assertEqual(args["instruction"], "hỏi tiếp link này")
        self.assertEqual(args["question"], "hỏi tiếp link này")


class TestRequestParserCurrentTime(unittest.TestCase):
    def test_current_time_question_routes_to_time_now(self) -> None:
        route = route_request("hôm nay là thứ mấy z")

        self.assertTrue(route.use_direct)
        self.assertEqual(route.route_type, "direct_deterministic")
        self.assertEqual(route.hint_tool, "time_now")

    def test_time_now_direct_args_are_empty(self) -> None:
        args = build_direct_tool_args("time_now", "hôm nay là thứ mấy z")

        self.assertEqual(args, {})
