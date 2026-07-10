from __future__ import annotations

from typing import Any

from langchain.tools import ToolRuntime, tool

from agent.execution_client import N8nToolGatewayClient
from agent.models import MiaContext
from agent.skills.common import _run_gateway_tool


def get_productivity_tools(tool_gateway: N8nToolGatewayClient) -> list:
    @tool("tasks_list")
    def tasks_list(limit: int = 20, tasklist_id: str = "@default", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """List Google Tasks."""
        return _run_gateway_tool(tool_gateway, "tasks.list", {"limit": max(1, min(limit, 100)), "tasklistId": tasklist_id}, runtime)

    @tool("tasks_list_due")
    def tasks_list_due(date: str = "", limit: int = 20, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """List tasks due on a date or today."""
        return _run_gateway_tool(tool_gateway, "tasks.list_due", {"date": date, "limit": max(1, min(limit, 100))}, runtime)

    @tool("tasks_list_overdue")
    def tasks_list_overdue(limit: int = 20, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """List overdue tasks."""
        return _run_gateway_tool(tool_gateway, "tasks.list_overdue", {"limit": max(1, min(limit, 100))}, runtime)

    @tool("tasks_create")
    def tasks_create(title: str, notes: str = "", due: str = "", tasklist_id: str = "@default", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create a Google Task after approval."""
        return _run_gateway_tool(tool_gateway, "tasks.create", {"title": title, "notes": notes, "due": due, "tasklistId": tasklist_id}, runtime)

    @tool("tasks_update")
    def tasks_update(task_id: str, title: str = "", notes: str = "", due: str = "", tasklist_id: str = "@default", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Update a Google Task after approval."""
        return _run_gateway_tool(tool_gateway, "tasks.update", {"taskId": task_id, "title": title, "notes": notes, "due": due, "tasklistId": tasklist_id}, runtime)

    @tool("tasks_complete")
    def tasks_complete(task_id: str, tasklist_id: str = "@default", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Mark a Google Task completed after approval."""
        return _run_gateway_tool(tool_gateway, "tasks.complete", {"taskId": task_id, "tasklistId": tasklist_id}, runtime)

    @tool("tasks_delete")
    def tasks_delete(task_id: str, tasklist_id: str = "@default", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Delete a Google Task after approval."""
        return _run_gateway_tool(tool_gateway, "tasks.delete", {"taskId": task_id, "tasklistId": tasklist_id}, runtime)

    @tool("contacts_search")
    def contacts_search(query: str, limit: int = 10, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Search contacts by name or email."""
        return _run_gateway_tool(tool_gateway, "contacts.search", {"query": query, "limit": max(1, min(limit, 50))}, runtime)

    @tool("contacts_get")
    def contacts_get(resource_name: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Get a contact by Google People resource name."""
        return _run_gateway_tool(tool_gateway, "contacts.get", {"resourceName": resource_name}, runtime)

    @tool("contacts_resolve_recipient")
    def contacts_resolve_recipient(name_or_email: str, limit: int = 5, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Resolve a recipient and return candidates when the identity is ambiguous."""
        return _run_gateway_tool(tool_gateway, "contacts.resolve_recipient", {"query": name_or_email, "limit": max(1, min(limit, 10))}, runtime)

    @tool("automation_list")
    def automation_list(runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """List Mia scheduled automations."""
        return _run_gateway_tool(tool_gateway, "automation.list", {}, runtime)

    @tool("automation_create")
    def automation_create(name: str, schedule: str, skill_name: str, input_text: str = "", runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Create a scheduled Mia skill after approval; schedule must be a five-field cron expression."""
        return _run_gateway_tool(tool_gateway, "automation.create", {"name": name, "schedule": schedule, "skillName": skill_name, "inputText": input_text}, runtime)

    @tool("automation_pause")
    def automation_pause(automation_id: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Pause a scheduled automation after approval."""
        return _run_gateway_tool(tool_gateway, "automation.pause", {"automationId": automation_id}, runtime)

    @tool("automation_resume")
    def automation_resume(automation_id: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Resume a scheduled automation after approval."""
        return _run_gateway_tool(tool_gateway, "automation.resume", {"automationId": automation_id}, runtime)

    @tool("automation_delete")
    def automation_delete(automation_id: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Delete a scheduled automation after approval."""
        return _run_gateway_tool(tool_gateway, "automation.delete", {"automationId": automation_id}, runtime)

    @tool("automation_run_now")
    def automation_run_now(automation_id: str, runtime: ToolRuntime[MiaContext] = None) -> str:  # type: ignore[assignment]
        """Run an automation immediately after approval."""
        return _run_gateway_tool(tool_gateway, "automation.run_now", {"automationId": automation_id}, runtime)

    return [
        tasks_list, tasks_list_due, tasks_list_overdue, tasks_create, tasks_update, tasks_complete, tasks_delete,
        contacts_search, contacts_get, contacts_resolve_recipient,
        automation_list, automation_create, automation_pause, automation_resume, automation_delete, automation_run_now,
    ]
