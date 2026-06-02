from __future__ import annotations

from dataclasses import dataclass

from mia_core.capabilities import DETERMINISTIC_DIRECT_TOOLS, DIRECT_ROUTE_TOOLS
from mia_core.request_parser import looks_multi_step, should_allow_direct_route, tool_hint_for_request


@dataclass(frozen=True)
class RouteDecision:
    route_type: str
    hint_tool: str
    agent_key: str
    reason: str

    @property
    def use_direct(self) -> bool:
        return self.route_type == "direct_deterministic"


def choose_agent_key(hint_tool: str, request_text: str) -> str:
    if looks_multi_step(request_text):
        if hint_tool.startswith(("calendar_", "gmail_", "drive_", "docs_", "sheets_")):
            return "google_full"
        return "general"

    if hint_tool.startswith("calendar_"):
        return "calendar"
    if hint_tool.startswith("gmail_"):
        return "gmail"
    if hint_tool.startswith(("drive_", "docs_", "sheets_")):
        return "workspace"
    return "general"


def route_request(request_text: str) -> RouteDecision:
    hint_tool = tool_hint_for_request(request_text)

    if hint_tool and hint_tool in DETERMINISTIC_DIRECT_TOOLS and should_allow_direct_route(hint_tool, request_text):
        return RouteDecision(
            route_type="direct_deterministic",
            hint_tool=hint_tool,
            agent_key="",
            reason="matched direct deterministic capability",
        )

    agent_key = choose_agent_key(hint_tool, request_text)
    route_type = "agentic_multistep" if looks_multi_step(request_text) else "agentic_domain"
    return RouteDecision(
        route_type=route_type,
        hint_tool=hint_tool,
        agent_key=agent_key,
        reason="use agent orchestration",
    )
