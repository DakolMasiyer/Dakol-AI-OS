import unittest
from pathlib import Path
import shutil

from core.workflow_policy import WorkflowFailure
from apps.syncmaster_ai.workflow import SyncMasterOrchestratedWorkflow
from apps.listening_farm_ai.workflow import ListeningFarmWorkflow
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
if "platform.app_registry" not in sys.modules:
    spec = importlib.util.spec_from_file_location("platform.app_registry", ROOT / "platform" / "app_registry.py")
    app_registry_module = importlib.util.module_from_spec(spec)
    sys.modules["platform.app_registry"] = app_registry_module
    spec.loader.exec_module(app_registry_module)

AppRegistry = sys.modules["platform.app_registry"].AppRegistry

class WorkflowOrchestrationTests(unittest.TestCase):
    def setUp(self):
        AppRegistry.reset()
        AppRegistry.register(ROOT / "apps" / "syncmaster_ai")
        AppRegistry.register(ROOT / "apps" / "listening_farm_ai")
        self.wf_sync = SyncMasterOrchestratedWorkflow("test-sync-wf")
        self.wf_farm = ListeningFarmWorkflow("test-farm-wf")

    def tearDown(self):
        AppRegistry.reset()
        if self.wf_sync.engine.checkpoints_dir.exists():
            shutil.rmtree(self.wf_sync.engine.checkpoints_dir.parent)
        if self.wf_farm.engine.checkpoints_dir.exists():
            shutil.rmtree(self.wf_farm.engine.checkpoints_dir.parent)

    def test_syncmaster_workflow_human_approval_pause(self):
        payload = {"human_approval": False}
        result = self.wf_sync.execute(payload)
        
        self.assertEqual(result["status"], "PAUSED")
        self.assertEqual(result["state"], "HUMAN_APPROVAL")
        
        # Verify checkpoint was generated immutably
        checkpoints = list(self.wf_sync.engine.checkpoints_dir.glob("*.json"))
        self.assertGreater(len(checkpoints), 0)

    def test_syncmaster_workflow_resume(self):
        # Pause at approval
        self.wf_sync.execute({"human_approval": False})
        
        # Manually approve
        checkpoint_path = self.wf_sync.engine.checkpoints_dir / "checkpoint_001.json"
        
        # Resume
        result = self.wf_sync.engine.resume_from_checkpoint(checkpoint_path, {"human_approval": True})
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(self.wf_sync.engine.state.current_stage, "COMPLETED")

    def test_listening_farm_full_workflow(self):
        result = self.wf_farm.execute({})
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(self.wf_farm.engine.state.current_stage, "COMPLETED")
        
        checkpoints = list(self.wf_farm.engine.checkpoints_dir.glob("*.json"))
        self.assertGreater(len(checkpoints), 0)

    def test_fail_closed_invalid_transition(self):
        # Hijack engine state to force invalid transition
        self.wf_farm.engine.state.current_stage = "SIGNAL_RANKING"
        self.wf_farm.engine.register_stage("SIGNAL_RANKING", lambda p: {"next_stage": "METADATA_EXTRACTION"})
        
        with self.assertRaises(WorkflowFailure) as ctx:
            self.wf_farm.execute({})
        
        self.assertEqual(ctx.exception.failure_type, "INVALID_TRANSITION")
