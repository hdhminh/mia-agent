from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    url: str
    token: str
    read_only_tools: frozenset[str]


class MCPAdapter:
    """Allowlisted HTTP MCP adapter restricted to explicitly read-only tools."""

    def __init__(self, *, servers_json: str, timeout_seconds: float = 30) -> None:
        self.timeout_seconds = timeout_seconds
        self.servers: dict[str, MCPServerConfig] = {}
        if not str(servers_json or "").strip():
            return
        payload = json.loads(servers_json)
        if not isinstance(payload, dict):
            raise ValueError("MIA_MCP_SERVERS_JSON must be an object.")
        for name, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            url = str(raw.get("url") or "").strip()
            if not url.startswith("https://"):
                raise ValueError(f"MCP server {name} must use HTTPS.")
            self.servers[str(name)] = MCPServerConfig(
                name=str(name),
                url=url,
                token=str(raw.get("token") or "").strip(),
                read_only_tools=frozenset(str(item) for item in raw.get("read_only_tools", []) if str(item).strip()),
            )

    def _request(self, server: MCPServerConfig, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if server.token:
            headers["Authorization"] = f"Bearer {server.token}"
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(server.url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        if data.get("error"):
            raise RuntimeError(str(data["error"]))
        return data.get("result") if isinstance(data.get("result"), dict) else {"result": data.get("result")}

    def list_tools(self, server_name: str) -> list[dict[str, Any]]:
        server = self.servers.get(server_name)
        if server is None:
            raise ValueError("MCP server is not allowlisted.")
        result = self._request(server, "tools/list")
        tools = result.get("tools") if isinstance(result, dict) else []
        return [tool for tool in tools if isinstance(tool, dict) and str(tool.get("name")) in server.read_only_tools]

    def call_read_only_tool(self, server_name: str, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        server = self.servers.get(server_name)
        if server is None:
            raise ValueError("MCP server is not allowlisted.")
        if tool_name not in server.read_only_tools:
            raise PermissionError("MCP tool is not explicitly allowlisted as read-only.")
        return self._request(server, "tools/call", {"name": tool_name, "arguments": arguments})
