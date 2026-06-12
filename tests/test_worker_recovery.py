import unittest
import time
from core.queue.worker import DistributedWorker

class WorkerRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.worker1 = DistributedWorker("crash_q")
        self.worker2 = DistributedWorker("crash_q")
        
        def mock_handler(payload):
            pass
            
        self.worker1.register_handler("crash_job", mock_handler)
        self.worker2.register_handler("crash_job", mock_handler)

    def test_worker_crash_recovery(self):
        job = self.worker1.enqueue("job-crash-1", "crash_job", {})
        
        # Worker 1 locks it with a very short lease (1 second) to simulate a crash/timeout
        locked = job.lock(self.worker1.worker_id, 1)
        self.assertTrue(locked)
        self.worker1._save_job(job)
        
        # Worker 2 tries to grab it immediately -> fails
        with self.assertRaises(RuntimeError):
            self.worker2.process_job("job-crash-1")
            
        # Wait 1.1 seconds for lease to expire
        time.sleep(1.1)
        
        # Worker 2 should now be able to recover and process it
        try:
            self.worker2.process_job("job-crash-1")
        except RuntimeError as e:
            self.fail(f"Worker 2 failed to recover job after lease expired: {e}")
            
        # Verify it completed
        job_final = self.worker2._load_job("job-crash-1")
        self.assertEqual(job_final.status, "COMPLETED")
