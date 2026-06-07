import unittest
from pathlib import Path
import shutil
import json
from core.grading.rubrics import Rubric
from core.grading.workflows import GradingWorkflow

class GradingReplayTests(unittest.TestCase):
    def setUp(self):
        self.rubric = Rubric(
            rubric_id="rubric-1",
            rubric_version="v1",
            section_weights={"A": 1.0},
            pass_threshold=0.8
        )
        self.workflow = GradingWorkflow(self.rubric, workflow_id="test-grading-wf")

    def tearDown(self):
        if self.workflow.engine.checkpoints_dir.exists():
            shutil.rmtree(self.workflow.engine.checkpoints_dir.parent)

    def test_grading_workflow_replayability(self):
        payload = {
            "submission_id": "sub-123",
            "rubric_version": "v1",
            "section_scores": {"A": 0.9},
            "requires_review": True,
            "human_reviewed": False
        }
        
        result = self.workflow.execute(payload)
        self.assertEqual(result["status"], "PAUSED")
        
        # Verify checkpoint generated
        checkpoints = list(self.workflow.engine.checkpoints_dir.glob("*.json"))
        self.assertGreater(len(checkpoints), 0)
        
        # Resume
        checkpoint_path = self.workflow.engine.checkpoints_dir / "checkpoint_001.json"
        
        data = json.loads(checkpoint_path.read_text())
        original_payload = data["payload"]
        
        resume_payload = original_payload.copy()
        resume_payload["human_reviewed"] = True
        
        result = self.workflow.engine.resume_from_checkpoint(checkpoint_path, resume_payload)
        
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["result"]["final_grade"]["final_score"], 0.9)
        self.assertTrue(result["result"]["final_grade"]["passed"])
        
        # Check execution fingerprint exists
        last_checkpoint = sorted(self.workflow.engine.checkpoints_dir.glob("*.json"))[-1]
        data = json.loads(last_checkpoint.read_text())
        state = json.loads(data["state"])
        self.assertIsNotNone(state["execution_fingerprint"])
