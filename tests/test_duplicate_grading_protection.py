import unittest
from pathlib import Path
import shutil
from core.grading.queue import GradingQueueManager, DuplicateGradingError

class DuplicateGradingProtectionTests(unittest.TestCase):
    def setUp(self):
        self.root_dir = Path(__file__).resolve().parent / "tmp_test_grading"
        self.manager = GradingQueueManager(root_dir=self.root_dir)

    def tearDown(self):
        if self.root_dir.exists():
            shutil.rmtree(self.root_dir)

    def test_duplicate_grading_rejected(self):
        job_id = "job-123"
        
        # First grading should pass
        result = self.manager.dispatch(job_id, lambda: {"status": "success"})
        self.assertEqual(result["status"], "success")
        
        # Second grading of SAME job should fail
        with self.assertRaises(DuplicateGradingError):
            self.manager.dispatch(job_id, lambda: {"status": "success"})

    def test_failed_grading_recoverable(self):
        job_id = "job-456"
        
        # First grading fails
        with self.assertRaises(ValueError):
            self.manager.dispatch(job_id, lambda: (_ for _ in ()).throw(ValueError("Test failure")))
            
        # Second grading can succeed since it didn't complete
        result = self.manager.dispatch(job_id, lambda: {"status": "recovered"})
        self.assertEqual(result["status"], "recovered")
