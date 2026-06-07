import unittest
from pathlib import Path

from core.tool_policy import ToolPolicyViolation, verify_tool_execution
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
if "platform.app_registry" not in sys.modules:
    spec = importlib.util.spec_from_file_location("platform.app_registry", ROOT / "platform" / "app_registry.py")
    app_registry_module = importlib.util.module_from_spec(spec)
    sys.modules["platform.app_registry"] = app_registry_module
    spec.loader.exec_module(app_registry_module)

AppRegistry = sys.modules["platform.app_registry"].AppRegistry

class ToolGovernanceTests(unittest.TestCase):
    def setUp(self):
        AppRegistry.reset()
        AppRegistry.register(ROOT / "apps" / "syncmaster_ai")
        AppRegistry.register(ROOT / "apps" / "listening_farm_ai")

    def test_authorized_tool_execution(self):
        # Should not raise any exception
        verify_tool_execution("syncmaster_ai", "syncmaster_analyze_metadata")
        verify_tool_execution("listening_farm_ai", "search_repo")

    def test_unauthorized_tool_execution_fails_closed(self):
        # SyncMaster AI shouldn't have access to search_repo
        with self.assertRaises(ToolPolicyViolation):
            verify_tool_execution("syncmaster_ai", "search_repo")
        
        # Listening Farm AI shouldn't have access to syncmaster tools
        with self.assertRaises(ToolPolicyViolation):
            verify_tool_execution("listening_farm_ai", "syncmaster_analyze_metadata")

    def test_unregistered_app_fails_closed(self):
        with self.assertRaises(ToolPolicyViolation):
            verify_tool_execution("rogue_app", "read_file")
