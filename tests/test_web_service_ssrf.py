from __future__ import annotations

import unittest
from unittest.mock import patch

from agent.skills.web_service.service import _is_private_host, _validate_public_url


class WebServiceSSRFGuardTest(unittest.TestCase):
    def test_rejects_credentials_in_url(self) -> None:
        with self.assertRaises(ValueError):
            _validate_public_url("http://user:pass@example.com/")

    def test_rejects_non_http_scheme(self) -> None:
        with self.assertRaises(ValueError):
            _validate_public_url("file:///etc/passwd")

    def test_rejects_loopback_and_private_hostnames(self) -> None:
        for url in ("http://localhost/", "http://127.0.0.1/", "http://10.0.0.1/", "http://192.168.1.1/"):
            with self.assertRaises(ValueError, msg=url):
                _validate_public_url(url)

    def test_private_host_detection(self) -> None:
        self.assertTrue(_is_private_host("localhost"))
        self.assertTrue(_is_private_host("127.0.0.1"))
        self.assertTrue(_is_private_host("10.1.2.3"))
        self.assertTrue(_is_private_host("192.168.0.5"))
        self.assertTrue(_is_private_host("172.16.0.1"))
        self.assertFalse(_is_private_host("172.15.0.1"))
        self.assertFalse(_is_private_host("example.com"))

    def test_rejects_private_resolved_address(self) -> None:
        with patch(
            "agent.skills.web_service.service.socket.getaddrinfo",
            return_value=[(0, 0, 0, "", ("192.168.50.50", 80))],
        ):
            with self.assertRaises(ValueError):
                _validate_public_url("http://public-named.example/")

    def test_accepts_public_url_with_public_resolution(self) -> None:
        with patch(
            "agent.skills.web_service.service.socket.getaddrinfo",
            return_value=[(0, 0, 0, "", ("93.184.216.34", 443))],
        ):
            _validate_public_url("https://example.com/")
            _validate_public_url("https://example.com/path?q=1")


if __name__ == "__main__":
    unittest.main()
