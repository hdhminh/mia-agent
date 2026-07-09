from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from agent.models import MiaContext
from agent.execution_client import N8nToolGatewayClient
from agent.skills.common import _run_gateway_tool, _normalize_instruction


def get_web_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool
    def news_get(
        topic: str = "",
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Get today's latest news. Use when the user asks for latest or current news."""
        return _run_gateway_tool(
            tool_gateway,
            "news.get",
            {"topic": topic},
            runtime,
        )

    @tool
    def search_web(
        query: str,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Search the web for current facts, references, and links."""
        return _run_gateway_tool(
            tool_gateway,
            "search.web",
            {"query": query},
            runtime,
        )

    @tool("read_url")
    def read_url_tool(
        url: str,
        instruction: str = "",
        fetch_strategy: str = "auto",
        max_chars: int = 0,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Read the content of a specific web page URL."""
        text = _normalize_instruction("web", "doc link", instruction or url)
        return _run_gateway_tool(
            tool_gateway,
            "web.read_url",
            {
                "url": url.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
                "fetchStrategy": fetch_strategy.strip() or "auto",
                "max_chars": max(0, int(max_chars or 0)),
            },
            runtime,
        )

    @tool("summarize_url")
    def summarize_url_tool(
        url: str,
        instruction: str = "",
        fetch_strategy: str = "auto",
        max_chars: int = 0,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Summarize the content of a specific web page URL."""
        text = _normalize_instruction("web", "tom tat link", instruction or url)
        return _run_gateway_tool(
            tool_gateway,
            "web.summarize_url",
            {
                "url": url.strip(),
                "instruction": text,
                "text": text,
                "prompt": text,
                "fetchStrategy": fetch_strategy.strip() or "auto",
                "max_chars": max(0, int(max_chars or 0)),
            },
            runtime,
        )

    @tool("ask_url")
    def ask_url_tool(
        url: str = "",
        question: str = "",
        instruction: str = "",
        fetch_strategy: str = "auto",
        max_chars: int = 0,
        runtime: ToolRuntime[MiaContext] = None,  # type: ignore[assignment]
    ) -> str:
        """Ask a follow-up question about a previously read or summarized URL."""
        text = _normalize_instruction("web", "hoi tiep link nay", question or instruction or url)
        payload = {
            "url": url.strip(),
            "instruction": text,
            "question": text,
            "text": text,
            "prompt": text,
            "fetchStrategy": fetch_strategy.strip() or "auto",
            "max_chars": max(0, int(max_chars or 0)),
        }
        return _run_gateway_tool(
            tool_gateway,
            "web.ask_url",
            payload,
            runtime,
        )

    return [news_get, search_web, read_url_tool, summarize_url_tool, ask_url_tool]
