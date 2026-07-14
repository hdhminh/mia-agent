from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class CodeRunnerError(RuntimeError):
    pass


@dataclass(frozen=True)
class CodeRunnerClient:
    base_url: str
    token: str = ""
    timeout_seconds: float = 60.0

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.base_url:
            raise CodeRunnerError("MIA code gateway chưa được cấu hình.")
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        try:
            response = httpx.post(
                url,
                json=payload,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise CodeRunnerError(f"Không gọi được Mia OpenCode gateway: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise CodeRunnerError(f"Mia OpenCode gateway trả response không phải JSON: HTTP {response.status_code}") from exc
        if response.status_code >= 400:
            message = str(data.get("detail") or data.get("error") or response.text).strip()
            raise CodeRunnerError(f"Mia OpenCode gateway lỗi HTTP {response.status_code}: {message}")
        if not isinstance(data, dict):
            raise CodeRunnerError("Mia OpenCode gateway trả payload không hợp lệ.")
        return data

    def list_projects(self) -> list[dict[str, Any]]:
        data = self.request("projects/status", {"project_id": ""})
        projects = data.get("projects")
        if isinstance(projects, list):
            return [item for item in projects if isinstance(item, dict)]
        project = data.get("project")
        if isinstance(project, dict):
            return [project]
        return []
