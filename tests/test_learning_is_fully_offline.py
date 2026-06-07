import unittest
from core.invariants import ExecutionPathContext, assert_learning_is_advisory_only

class LearningOfflineTests(unittest.TestCase):
    
    def test_learning_access_in_execution_path_raises(self):
        # Verify that entering the execution path turns learning completely off
        with ExecutionPathContext():
            # assert_learning_is_advisory_only asserts that get_learning_recommendations 
            # will raise a RuntimeError("LEARNING SYSTEM VIOLATION") during execution
            try:
                assert_learning_is_advisory_only()
            except AssertionError as e:
                self.fail(f"Learning was not fully offline! {e}")

    def test_learning_access_outside_execution_path_succeeds(self):
        # Outside of the execution context, learning access does not raise the violation error.
        # But assert_learning_is_advisory_only checks IF it's in the execution path.
        # So we just test that get_learning_recommendations itself works outside.
        from memory.learning import get_learning_recommendations
        try:
            recs = get_learning_recommendations()
            self.assertIsInstance(recs, dict)
        except RuntimeError as e:
            if str(e) == "LEARNING SYSTEM VIOLATION":
                self.fail("Learning offline isolation is blocking offline access as well!")
            else:
                raise e

if __name__ == "__main__":
    unittest.main()
