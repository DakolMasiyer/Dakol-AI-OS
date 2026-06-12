import unittest
from core.queue.worker import DistributedWorker

class RetryIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.worker = DistributedWorker("retry_q")
        
        self.fail_count = 0
        def flaky_handler(payload):
            if self.fail_count < 2:
                self.fail_count += 1
                raise ValueError("Flaky network")
            return "Success"
            
        self.worker.register_handler("flaky_job", flaky_handler)

    def test_deterministic_retries_and_recovery(self):
        job = self.worker.enqueue("job-retry-1", "flaky_job", {})
        
        # Attempt 1 -> fails
        with self.assertRaises(ValueError):
            self.worker.process_job("job-retry-1")
            
        job_after_1 = self.worker._load_job("job-retry-1")
        self.assertEqual(job_after_1.status, "PENDING")  # Released lease
        self.assertEqual(job_after_1.attempts, 1)
        self.assertEqual(len(job_after_1.error_history), 1)
        
        # Attempt 2 -> fails
        with self.assertRaises(ValueError):
            self.worker.process_job("job-retry-1")
            
        job_after_2 = self.worker._load_job("job-retry-1")
        self.assertEqual(job_after_2.status, "PENDING")
        self.assertEqual(job_after_2.attempts, 2)
        
        # Attempt 3 -> succeeds
        self.worker.process_job("job-retry-1")
        
        job_final = self.worker._load_job("job-retry-1")
        self.assertEqual(job_final.status, "COMPLETED")
        self.assertEqual(job_final.attempts, 3)
        self.assertEqual(len(job_final.error_history), 2)  # Audit trail intact
