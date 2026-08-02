from __future__ import annotations

from agent.memory.repository import MemoryRepository
from agent.execution_client import N8nToolGatewayClient

from agent.skills.memory import get_memory_tools
from agent.skills.simple import get_simple_tools
from agent.skills.web import get_web_tools
from agent.skills.media import get_media_tools
from agent.skills.github import get_github_tools
from agent.skills.google import get_google_tools
from agent.skills.google_maps import get_google_maps_tools
from agent.skills.github_write import get_github_write_tools
from agent.skills.productivity import get_productivity_tools
from agent.skills.smarthome import get_smarthome_tools
from agent.skills.code_runner import get_code_tools


def build_tools(
    *,
    memory_repo: MemoryRepository,
    tool_gateway: N8nToolGatewayClient,
    code_default_project_id: str = "",
) -> list:
    tools = []
    tools.extend(get_memory_tools(memory_repo))
    tools.extend(get_simple_tools(tool_gateway))
    tools.extend(get_web_tools(tool_gateway))
    tools.extend(get_media_tools(tool_gateway))
    tools.extend(get_github_tools(tool_gateway))
    tools.extend(get_github_write_tools(tool_gateway))
    tools.extend(get_google_tools(tool_gateway))
    tools.extend(get_google_maps_tools(tool_gateway))
    tools.extend(get_productivity_tools(tool_gateway))
    tools.extend(get_smarthome_tools(tool_gateway))
    tools.extend(get_code_tools(default_project_id=code_default_project_id, tool_gateway=tool_gateway))
    return tools
