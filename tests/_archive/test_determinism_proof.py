import unittest
from unittest.mock import patch

from scripts.semantic_router import route_task_semantically, _EMBEDDING_CACHE
from core.invariants import ExecutionPathContext, verify_system_invariants

class DeterminismProofTests(unittest.TestCase):
    
    def test_hash_consistency(self):
        # TEST 1 — HASH CONSISTENCY
        # run same input 100 times and assert identical attributes
        task = "implement a database migration script for the new Supabase schema"
        
        with ExecutionPathContext():
            first_decision = route_task_semantically(task)
            
            for _ in range(100):
                decision = route_task_semantically(task)
                self.assertEqual(decision.model, first_decision.model)
                self.assertEqual(decision.intent, first_decision.intent)
                self.assertEqual(decision.route, first_decision.route)
                self.assertEqual(decision.execution_target, first_decision.execution_target)
                self.assertEqual(decision.confidence, first_decision.confidence)
                
                # Check system invariants
                verify_system_invariants(task=task, decision=decision)

    def test_state_independence(self):
        # TEST 2 — STATE INDEPENDENCE
        # modify learning_state drastically and assert ZERO change in output
        task = "write a FastAPI endpoint for checking user session logs"
        
        # Base decision without custom state
        with ExecutionPathContext():
            base_decision = route_task_semantically(task)
            
        # Drastic state A (recommending local model for software_engineering)
        state_a = {
            "recommendations": {
                "model": {
                    "software_engineering": {
                        "recommended_model": "local",
                        "confidence": 0.99,
                        "reason": "Force local model"
                    }
                }
            },
            "analytics": {
                "intents": {
                    "software_engineering": {
                        "count": 100
                    }
                }
            }
        }
        
        # Drastic state B (recommending claude model for software_engineering)
        state_b = {
            "recommendations": {
                "model": {
                    "software_engineering": {
                        "recommended_model": "claude",
                        "confidence": 0.99,
                        "reason": "Force Claude model"
                    }
                }
            },
            "analytics": {
                "intents": {
                    "software_engineering": {
                        "count": 100
                    }
                }
            }
        }
        
        # Rerun under state_a
        with patch("memory.learning.load_learning_state", return_value=state_a):
            with ExecutionPathContext():
                decision_a = route_task_semantically(task)
                
        # Rerun under state_b
        with patch("memory.learning.load_learning_state", return_value=state_b):
            with ExecutionPathContext():
                decision_b = route_task_semantically(task)
                
        # Assert zero change in runtime execution targets
        self.assertEqual(decision_a.model, base_decision.model)
        self.assertEqual(decision_b.model, base_decision.model)
        self.assertEqual(decision_a.route, base_decision.route)
        self.assertEqual(decision_b.route, base_decision.route)
        self.assertEqual(decision_a.execution_target, base_decision.execution_target)
        self.assertEqual(decision_b.execution_target, base_decision.execution_target)

    def test_process_reset_consistency(self):
        # TEST 3 — PROCESS RESET CONSISTENCY
        # restart system simulation (clearing thread local routing history and cache)
        # and assert that outputs remain identical
        task = "evaluate licensing options and synthesis of pipeline trade-offs"
        
        # Run 1
        with ExecutionPathContext():
            decision_1 = route_task_semantically(task)
            
        # Simulate process restart (clear thread local history and cache)
        from scripts.semantic_router import get_routing_history
        get_routing_history().clear()
        _EMBEDDING_CACHE.clear()
        
        # Run 2
        with ExecutionPathContext():
            decision_2 = route_task_semantically(task)
            
        self.assertEqual(decision_1.model, decision_2.model)
        self.assertEqual(decision_1.intent, decision_2.intent)
        self.assertEqual(decision_1.route, decision_2.route)
        self.assertEqual(decision_1.execution_target, decision_2.execution_target)

    def test_cache_invariance(self):
        # TEST 4 — CACHE INVARIANCE
        # Warm cache vs cold cache output must match exactly
        task = "analyze BPM tempo, genre and moods of audio files"
        
        # Cold cache run (cache is cleared before start)
        _EMBEDDING_CACHE.clear()
        with ExecutionPathContext():
            decision_cold = route_task_semantically(task)
            
        # Warm cache run (cache contains values from previous run)
        with ExecutionPathContext():
            decision_warm = route_task_semantically(task)
            
        self.assertEqual(decision_cold.model, decision_warm.model)
        self.assertEqual(decision_cold.intent, decision_warm.intent)
        self.assertEqual(decision_cold.route, decision_warm.route)
        self.assertEqual(decision_cold.execution_target, decision_warm.execution_target)
        
    def test_learning_state_violation_guard(self):
        # Verify that accessing learning state during execution throws RuntimeError
        from memory.learning import load_learning_state
        
        with ExecutionPathContext():
            with self.assertRaises(RuntimeError) as ctx:
                load_learning_state()
            self.assertEqual(str(ctx.exception), "LEARNING SYSTEM VIOLATION")

    def test_verify_system_invariants_no_args(self):
        # Verify that the invariants check runs cleanly with no arguments
        verify_system_invariants()

if __name__ == "__main__":
    unittest.main()
