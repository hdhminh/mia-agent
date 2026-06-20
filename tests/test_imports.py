from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestRuntimeImports(unittest.TestCase):
    def test_core_runtime_modules_import(self) -> None:
        import agent.service as agent_module
        import agent.api as app_module
        import agent.skills as tools_module
        import agent.skills.web as web_tools_module
        import agent.skills.web_service.routes as web_routes_module
        import agent.skills.web_service.service as web_service_module

        self.assertTrue(hasattr(app_module, "app"))
        self.assertTrue(hasattr(agent_module, "MiaAgentService"))
        self.assertTrue(hasattr(tools_module, "build_tools"))
        self.assertTrue(hasattr(web_tools_module, "get_web_tools"))
        self.assertTrue(hasattr(web_routes_module, "router"))
        self.assertTrue(hasattr(web_service_module, "WebService"))
