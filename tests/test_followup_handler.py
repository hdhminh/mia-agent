from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from agent.models import MiaChatRequest


class FollowupHandlerTest(unittest.TestCase):
    def _make_service(self, rows=None, model_result=None):
        service = SimpleNamespace(
            memory_repo=MagicMock(),
            document_followup_model=MagicMock(),
            document_followup_fallback_model=None,
            _learning_guidance_text=MagicMock(return_value=""),
            _cache_trace=MagicMock(return_value={}),
        )
        service.memory_repo.search = MagicMock(return_value=rows or [])
        service._invoke_model_with_fallback = MagicMock(
            return_value=(SimpleNamespace(content=model_result or "Trả lời followup."), "primary")
        )
        return service

    def test_non_followup_returns_none(self):
        from agent.brain.followup_handler import FollowupHandler

        service = self._make_service()
        handler = FollowupHandler(service)
        req = MiaChatRequest(chat_id="c", text="kể chuyện cười đi")
        self.assertIsNone(handler._try_document_memory_followup(req))
        service.memory_repo.search.assert_not_called()

    def test_followup_without_memory_returns_none(self):
        from agent.brain.followup_handler import FollowupHandler

        service = self._make_service(rows=[])
        handler = FollowupHandler(service)
        req = MiaChatRequest(chat_id="c", text="trong file này nói gì?")
        self.assertIsNone(handler._try_document_memory_followup(req))

    def test_followup_with_memory_answers(self):
        from agent.brain.followup_handler import FollowupHandler

        rows = [
            {"title": "Báo cáo T1", "chunk_text": "Doanh thu tăng 20%", "id": 1},
        ]
        service = self._make_service(rows=rows)
        service._record_learning_event = MagicMock()
        handler = FollowupHandler(service)
        req = MiaChatRequest(chat_id="c", text="doanh thu trong file này tăng bao nhiêu?")
        resp = handler._try_document_memory_followup(req)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.final_text, "Trả lời followup.")

    def test_url_followup_uses_url_memory(self):
        from agent.brain.followup_handler import FollowupHandler

        rows = [
            {"title": "Article", "chunk_text": "Học phí là 10 triệu", "id": 2},
        ]
        service = self._make_service(rows=rows)
        service._record_learning_event = MagicMock()
        handler = FollowupHandler(service)
        req = MiaChatRequest(chat_id="c", text="link đó nói gì về học phí?")
        resp = handler._try_url_memory_followup(req)
        self.assertIsNotNone(resp)


if __name__ == "__main__":
    unittest.main()
