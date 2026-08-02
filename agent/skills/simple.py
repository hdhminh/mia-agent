from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.brain.time_utils import build_current_date_response
from agent.skills.common import _run_gateway_tool


def get_simple_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool
    def weather_get(
        location: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the current weather for a city or place."""
        return _run_gateway_tool(
            tool_gateway,
            "weather.get",
            {"location": location},
            runtime,
        )

    @tool
    def gold_get_price(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the latest SJC or 9999 gold price."""
        return _run_gateway_tool(tool_gateway, "gold.get_price", {}, runtime)


    @tool
    def time_now(
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get the current date and time in the configured timezone."""
        timezone = str(getattr(getattr(runtime, "context", None), "timezone", "Asia/Ho_Chi_Minh") or "Asia/Ho_Chi_Minh").strip()
        return str(build_current_date_response(timezone)["text"])

    @tool
    def shortlink_create(
        url: str,
        ttl: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Create a short link through n8n. The ttl can be like 24h, 7d, 30d, or 'vinh vien'."""
        return _run_gateway_tool(
            tool_gateway,
            "shortlink.create",
            {"url": url, "ttl": ttl},
            runtime,
        )

    @tool
    def notify_telegram(
        text: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Send a Telegram message to the current chat. Used for reminders and proactive notifications."""
        chat_id = str(getattr(getattr(runtime, "context", None), "chat_id", "") or "").strip()
        return _run_gateway_tool(
            tool_gateway,
            "notify.telegram",
            {"text": text, "chatId": chat_id},
            runtime,
        )

    return [weather_get, gold_get_price, shortlink_create, time_now, notify_telegram]
