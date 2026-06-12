import unittest
import shutil
import time
from core.api import WorkflowEngine, WorkflowPolicyEngine
from pathlib import Path

class AsyncReplayTests(unittest.TestCase):
    def setUp(self):
        self.policy = WorkflowPolicyEngine(allowed_transitions={
            "START": ["ASYNC_GROUP"],
            "ASYNC_GROUP": ["COMPLETED"]
        })
        self.workflow_id = f"async-test-{int(time.time())}"
        self.engine = WorkflowEngine(
            app_id="test.async",
            workflow_id=self.workflow_id,
            policy=self.policy,
            initial_stage="START"
        )
        
        self.engine.register_stage("START", lambda p: {"status": "success", "next_stage": "ASYNC_GROUP"})
        self.engine.register_stage("fetch_a", lambda p: {"data": "A"})
        self.engine.register_stage("fetch_b", lambda p: {"data": "B"})
        
        # Register the async group
        self.engine.register_concurrent_stage("ASYNC_GROUP", ["fetch_a", "fetch_b"])

    def tearDown(self):
        if self.engine.checkpoints_dir.exists():
            shutil.rmtree(self.engine.checkpoints_dir.parent)

    def test_async_stage_determinism(self):
        result = self.engine.execute({"init": True})
        
        self.assertEqual(result["status"], "COMPLETED")
        # Ensure results were aggregated deterministically
        aggregated = result["result"]["async_results"]
        self.assertEqual(aggregated["fetch_a"]["data"], "A")
        self.assertEqual(aggregated["fetch_b"]["data"], "B")
        
        # Verify checkpoint fingerprint exists
        checkpoints = sorted(self.engine.checkpoints_dir.glob("*.json"))
        self.assertGreater(len(checkpoints), 0)
