import unittest
import time
from core.queue.worker import DistributedWorker
from core.queue.jobs import JobState

class DistributedQueueTests(unittest.TestCase):
    def setUp(self):
        self.worker1 = DistributedWorker("test_q")
        self.worker2 = DistributedWorker("test_q")
        
        self.processed = []
        def handler(payload):
            self.processed.append(payload["data"])
            
        self.worker1.register_handler("test_job", handler)
        self.worker2.register_handler("test_job", handler)

    def test_job_enqueue_and_process(self):
        job = self.worker1.enqueue("job-1", "test_job", {"data": "test_1"})
        
        # Verify job is pending
        self.assertEqual(job.status, "PENDING")
        self.assertIsNone(job.lease)
        
        # Worker 1 processes it
        self.worker1.process_job("job-1")
        self.assertEqual(self.processed, ["test_1"])
        
        # Reload to verify status
        job_after = self.worker1._load_job("job-1")
        self.assertEqual(job_after.status, "COMPLETED")
        self.assertIsNone(job_after.lease)

    def test_worker_lease_prevents_duplicate_execution(self):
        job = self.worker1.enqueue("job-2", "test_job", {"data": "test_2"})
        
        # Lock it with worker 1
        locked = job.lock(self.worker1.worker_id, 300)
        self.assertTrue(locked)
        self.worker1._save_job(job)
        
        # Worker 2 tries to process
        with self.assertRaises(RuntimeError) as ctx:
            self.worker2.process_job("job-2")
        
        self.assertIn("Failed to acquire lease", str(ctx.exception))
