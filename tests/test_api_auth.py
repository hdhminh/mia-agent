from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from agent.api import app
from agent.rate_limit import SlidingWindowRateLimiter


class _FakeSettings:
    core_api_token = "secret-token"


def _setup_state(*, rate_limit: int = 10) -> None:
    app.state.settings = _FakeSettings()
    app.state.rate_limiter = SlidingWindowRateLimiter(limit=rate_limit, window_seconds=60)


class ApiAuthTests(unittest.TestCase):
    def setUp(self) -> None:
        _setup_state()

    def test_health_is_public(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_chat_requires_token(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/mia/chat", json={"chat_id": "c", "text": "hi"})
        self.assertEqual(resp.status_code, 401)

    def test_chat_rejects_wrong_token(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/mia/chat",
            json={"chat_id": "c", "text": "hi"},
            headers={"x-mia-core-token": "wrong-token"},
        )
        self.assertEqual(resp.status_code, 401)

    def test_chat_accepts_valid_token_past_auth(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/mia/chat",
            json={"chat_id": "c", "text": "hi"},
            headers={"x-mia-core-token": "secret-token"},
        )
        # Auth passed (reaches endpoint); endpoint fails at app.state.agent_service (no lifespan), which is not 401/503.
        self.assertNotIn(resp.status_code, (401, 503))

    def test_bearer_token_works(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/mia/chat",
            json={"chat_id": "c", "text": "hi"},
            headers={"Authorization": "Bearer secret-token"},
        )
        self.assertNotIn(resp.status_code, (401, 503))

    def test_rate_limit_after_exceeding(self) -> None:
        _setup_state(rate_limit=2)
        client = TestClient(app, raise_server_exceptions=False)
        headers = {"x-mia-core-token": "secret-token"}
        client.post("/mia/chat", json={"chat_id": "c", "text": "hi"}, headers=headers)
        client.post("/mia/chat", json={"chat_id": "c", "text": "hi"}, headers=headers)
        third = client.post("/mia/chat", json={"chat_id": "c", "text": "hi"}, headers=headers)
        self.assertEqual(third.status_code, 429)

    def test_auth_fails_closed_when_token_not_configured(self) -> None:
        app.state.settings = _FakeSettings()
        app.state.settings.core_api_token = ""
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post("/mia/chat", json={"chat_id": "c", "text": "hi"})
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    unittest.main()
