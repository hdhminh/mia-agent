from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LANGCHAIN_ROOT = ROOT / "langchain_core"
if str(LANGCHAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(LANGCHAIN_ROOT))


class TestRuntimeImports(unittest.TestCase):
    def test_core_runtime_modules_import(self) -> None:
        import mia_core.agent as agent_module
        import mia_core.app as app_module
        import mia_core.tools as tools_module
        import mia_core.tool_defs.web as web_tools_module
        import mia_core.web.routes as web_routes_module
        import mia_core.web.service as web_service_module

        self.assertTrue(hasattr(app_module, "app"))
        self.assertTrue(hasattr(agent_module, "MiaAgentService"))
        self.assertTrue(hasattr(tools_module, "build_tools"))
        self.assertTrue(hasattr(web_tools_module, "get_web_tools"))
        self.assertTrue(hasattr(web_routes_module, "router"))
        self.assertTrue(hasattr(web_service_module, "WebService"))
