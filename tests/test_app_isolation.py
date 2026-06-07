import json
import shutil
from pathlib import Path
from unittest import TestCase

import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
if "platform.app_registry" not in sys.modules:
    spec = importlib.util.spec_from_file_location("platform.app_registry", ROOT / "platform" / "app_registry.py")
    app_registry_module = importlib.util.module_from_spec(spec)
    sys.modules["platform.app_registry"] = app_registry_module
    spec.loader.exec_module(app_registry_module)

AppRegistry = sys.modules["platform.app_registry"].AppRegistry

from apps.syncmaster_ai.app import SyncMasterAI


class AppIsolationTests(TestCase):
    def setUp(self):
        AppRegistry.reset()
        self.trace_dir = ROOT / "logs" / "execution" / "syncmaster_ai"
        if self.trace_dir.exists():
            shutil.rmtree(self.trace_dir)

    def tearDown(self):
        AppRegistry.reset()
        if self.trace_dir.exists():
            shutil.rmtree(self.trace_dir)

    def test_app_registry_registration(self):
        syncmaster_path = ROOT / "apps" / "syncmaster_ai"
        AppRegistry.register(syncmaster_path)
        manifest = AppRegistry.get_manifest("syncmaster_ai")
        self.assertEqual(manifest.app_id, "syncmaster_ai")

    def test_app_trace_isolation(self):
        app = SyncMasterAI()
        
        # Verify the app traces to its own namespace
        # (This will just invoke the router with fallback model, resulting in an error string if no API keys,
        # but the trace will still be written).
        result = app.execute("Hello, this is a test task for syncmaster_ai")
        
        # Verify that a trace file was created in the specific app namespace
        self.assertTrue(self.trace_dir.exists(), "Trace directory was not created")
        
        traces = list(self.trace_dir.glob("*.json"))
        self.assertGreater(len(traces), 0, "No trace file was generated in the app namespace")
        
        # Verify the execution ID starts with the app_id
        trace_data = json.loads(traces[0].read_text())
        self.assertTrue(trace_data["execution_id"].startswith("syncmaster_ai-"))
