from __future__ import annotations

from mia_core.memory import MemoryRepository
from mia_core.n8n_client import N8nToolGatewayClient

from mia_core.tool_defs.memory import get_memory_tools
from mia_core.tool_defs.simple import get_simple_tools
from mia_core.tool_defs.web import get_web_tools
from mia_core.tool_defs.media import get_media_tools
from mia_core.tool_defs.github import get_github_tools
from mia_core.tool_defs.google import get_google_tools


def build_tools(
    *,
    memory_repo: MemoryRepository,
    tool_gateway: N8nToolGatewayClient,
) -> list:
    tools = []
    tools.extend(get_memory_tools(memory_repo))
    tools.extend(get_simple_tools(tool_gateway))
    tools.extend(get_web_tools(tool_gateway))
    tools.extend(get_media_tools(tool_gateway))
    tools.extend(get_github_tools(tool_gateway))
    tools.extend(get_google_tools(tool_gateway))
    return tools
