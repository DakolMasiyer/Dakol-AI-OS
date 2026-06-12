import unittest
from pathlib import Path
import shutil
from core.governance.quotas import SupabaseQuotaClient, QuotaExhaustedError

class QuotaFailoverTests(unittest.TestCase):
    def setUp(self):
        self.db_path = Path(__file__).resolve().parent / "tmp_supabase_mock.db"
        if self.db_path.exists():
            self.db_path.unlink()
        self.client = SupabaseQuotaClient(self.db_path)

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()

    def test_quota_exhaustion_and_failover(self):
        # Default configured limit for worldcup_ai gemini is 100
        
        # Consume 90 -> succeeds
        success = self.client.consume_quota("worldcup_ai", "gemini", 90)
        self.assertTrue(success)
        
        # Remaining should be 10
        rem = self.client.get_remaining_quota("worldcup_ai", "gemini")
        self.assertEqual(rem, 10)
        
        # Try to consume 20 -> fails
        with self.assertRaises(QuotaExhaustedError):
            self.client.consume_quota("worldcup_ai", "gemini", 20)
            
        # Remaining should still be 10 (no partial write)
        rem_after = self.client.get_remaining_quota("worldcup_ai", "gemini")
        self.assertEqual(rem_after, 10)
