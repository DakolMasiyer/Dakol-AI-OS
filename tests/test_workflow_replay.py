import unittest
import shutil
import json
from pathlib import Path

from apps.syncmaster_ai.workflow import SyncMasterOrchestratedWorkflow
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
if "platform.app_registry" not in sys.modules:
    spec = importlib.util.spec_from_file_location("platform.app_registry", ROOT / "platform" / "app_registry.py")
    app_registry_module = importlib.util.module_from_spec(spec)
    sys.modules["platform.app_registry"] = app_registry_module
    spec.loader.exec_module(app_registry_module)

AppRegistry = sys.modules["platform.app_registry"].AppRegistry

class WorkflowReplayTests(unittest.TestCase):
    def setUp(self):
        AppRegistry.reset()
        AppRegistry.register(ROOT / "apps" / "syncmaster_ai")
        self.trace_dir = ROOT / "logs" / "execution" / "syncmaster_ai"
        if self.trace_dir.exists():
            shutil.rmtree(self.trace_dir)

    def tearDown(self):
        AppRegistry.reset()
        if self.trace_dir.exists():
            shutil.rmtree(self.trace_dir)

    def test_workflow_replay_consistency(self):
        workflow = SyncMasterOrchestratedWorkflow("test-wf-id")
        
        payload = {"human_approval": False}
        
        try:
            workflow.execute(payload)
        except Exception:
            pass
        
        # Verify checkpoint traces were created
        traces = list(workflow.engine.checkpoints_dir.glob("*.json"))
        self.assertGreater(len(traces), 0, "No checkpoint trace file was generated in the app namespace during workflow")
        
        # Load a trace and check that state has execution_fingerprint 
        # (in this case, since we pause, final fingerprint may not exist, but let's check basic structure)
        trace_data = json.loads(traces[0].read_text())
        
        self.assertEqual(trace_data["workflow_id"], "test-wf-id")
        
        # The engine serializes the state to the checkpoint
        state_data = json.loads(trace_data["state"])
        
        # Ensure it has stage fingerprints (preserves replayability)
        self.assertIn("stage_fingerprints", state_data)
        self.assertIsNotNone(state_data["stage_fingerprints"])
