from __future__ import annotations

from dataclasses import dataclass

from mia_core.capabilities import DETERMINISTIC_DIRECT_TOOLS
from mia_core.request_parser import RequestProfile, infer_request_profile, looks_multi_step, should_allow_direct_route


@dataclass(frozen=True)
class RouteDecision:
    route_type: str
    domain: str
    hint_tool: str
    agent_key: str
    direct_confident: bool
    reason: str

    @property
    def use_direct(self) -> bool:
        return self.route_type == "direct_deterministic"


def choose_agent_key(profile: RequestProfile, request_text: str) -> str:
    hint_tool = profile.hint_tool
    if looks_multi_step(request_text):
        if profile.domain in {"calendar", "gmail", "workspace", "google_full"}:
            return "google_full"
        return "general"

    if profile.domain == "calendar":
        return "calendar"
    if profile.domain == "gmail":
        return "gmail"
    if profile.domain == "github":
        return "github"
    if profile.domain == "google_full":
        return "google_full"
    if profile.domain == "media":
        return "media"
    if profile.domain == "workspace":
        return "workspace"
    if hint_tool.startswith("calendar_"):
        return "calendar"
    if hint_tool.startswith("gmail_"):
        return "gmail"
    if hint_tool.startswith("github_"):
        return "github"
    if hint_tool.startswith(("drive_", "docs_", "sheets_")):
        return "workspace"
    return "general"


def route_request(request_text: str, metadata: dict | None = None) -> RouteDecision:
    profile = infer_request_profile(request_text, metadata)
    hint_tool = profile.hint_tool

    if hint_tool and hint_tool in DETERMINISTIC_DIRECT_TOOLS and should_allow_direct_route(hint_tool, request_text, metadata):
        return RouteDecision(
            route_type="direct_deterministic",
            domain=profile.domain,
            hint_tool=hint_tool,
            agent_key="",
            direct_confident=profile.direct_confident,
            reason=profile.reason,
        )

    agent_key = choose_agent_key(profile, request_text)
    route_type = "agentic_multistep" if looks_multi_step(request_text) else "agentic_domain"
    return RouteDecision(
        route_type=route_type,
        domain=profile.domain,
        hint_tool=hint_tool,
        agent_key=agent_key,
        direct_confident=profile.direct_confident,
        reason=profile.reason,
    )
