from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from mia_core.models import MiaContext


@dataclass(frozen=True)
class ToolGatewayResult:
    ok: bool
    tool: str
    text: str
    payload: dict[str, Any]


class N8nToolGatewayClient:
    def __init__(self, url: str, token: str, timeout_seconds: float) -> None:
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds

    def run_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
        context: MiaContext,
    ) -> ToolGatewayResult:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["x-mia-tool-token"] = self.token

        payload = {
            "tool": tool_name,
            "args": args,
            "chatId": context.chat_id,
            "userId": context.user_id,
            "requestId": context.request_id,
            "deliveryMode": "return",
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(self.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        ok = bool(data.get("ok", False))
        text = str(data.get("text") or data.get("result") or "").strip()
        if not ok:
            error = str(data.get("error") or text or "Unknown n8n tool gateway error.")
            raise RuntimeError(f"{tool_name} failed: {error}")

        return ToolGatewayResult(ok=True, tool=tool_name, text=text, payload=data)
