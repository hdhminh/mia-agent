from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPT_MAINTENANCE_ROOT = ROOT / "scripts" / "maintenance"
if str(SCRIPT_MAINTENANCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_MAINTENANCE_ROOT))

from workflow_validation import validate_workflow_data, validate_workflow_file


class TestWorkflowArtifacts(unittest.TestCase):
    def test_web_master_routes_to_real_workflow_id(self) -> None:
        path = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))
        route_node = next(node for node in workflow["nodes"] if node.get("name") == "Route Tool")
        js_code = str(route_node["parameters"]["jsCode"])

        match = re.search(r"'web\.master':\s*'([^']+)'", js_code)
        self.assertIsNotNone(match, "web.master mapping is missing from Route Tool")
        workflow_id = match.group(1)

        self.assertNotEqual(workflow_id, "Sub-workflow: Web Master")
        self.assertGreaterEqual(len(workflow_id), 12)
        self.assertNotIn(" ", workflow_id)

    def test_error_monitor_has_chat_id_fallback(self) -> None:
        path = ROOT / "execution" / "monitors" / "workflow_error_monitor.json"
        workflow = json.loads(path.read_text(encoding="utf-8"))

        if_node = next(node for node in workflow["nodes"] if node.get("name") == "Co Gui Bao Loi?")
        telegram_node = next(node for node in workflow["nodes"] if node.get("name") == "Gui Loi Telegram")
        classify_node = next(node for node in workflow["nodes"] if node.get("name") == "Classify Error")

        if_expr = str(if_node["parameters"]["conditions"]["boolean"][0]["value1"])
        chat_id_expr = str(telegram_node["parameters"]["bodyParameters"]["parameters"][0]["value"])
        classify_code = str(classify_node["parameters"]["jsCode"])

        self.assertIn("execution?.error?.context?.request?.body?.chat_id", if_expr)
        self.assertIn("TELEGRAM_ADMIN_CHAT_ID", if_expr)
        self.assertIn("execution?.error?.context?.request?.body?.chat_id", chat_id_expr)
        self.assertIn("TELEGRAM_ADMIN_CHAT_ID", chat_id_expr)
        self.assertIn("currentExecutionId", classify_code)
        self.assertIn("errorResponse?.executionId", classify_code)
        self.assertIn("skipNotify = isParentCascade", classify_code)
        self.assertIn("propagatedExecutionId !== currentExecutionId", classify_code)

    def test_workflow_validator_accepts_current_gateway_and_monitor(self) -> None:
        gateway = ROOT / "execution" / "gateway" / "workflow_mia_tool_gateway.json"
        error_monitor = ROOT / "execution" / "monitors" / "workflow_error_monitor.json"

        self.assertEqual(validate_workflow_file(gateway), [])
        self.assertEqual(validate_workflow_file(error_monitor), [])

    def test_workflow_validator_rejects_human_readable_subworkflow_id(self) -> None:
        bad_workflow = {
            "name": "Mia: Tool Gateway",
            "nodes": [
                {
                    "name": "Route Tool",
                    "type": "n8n-nodes-base.code",
                    "parameters": {
                        "jsCode": "const workflowMap = { 'web.master': 'Sub-workflow: Web Master' };",
                    },
                }
            ],
            "connections": {},
        }

        issues = validate_workflow_data(bad_workflow, source="<memory>")
        self.assertTrue(any("web.master" in issue for issue in issues), issues)
        self.assertTrue(any("does not look like a workflow ID" in issue for issue in issues), issues)
