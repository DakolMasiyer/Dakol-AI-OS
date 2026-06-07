import unittest
import threading
from unittest.mock import patch
from scripts.semantic_router import route_task_semantically
from core.invariants import assert_routing_determinism

class AdversarialDriftTests(unittest.TestCase):
    
    def test_multi_thread_routing_stability(self):
        # TEST 1: Deterministic Routing Stability (Multi-thread)
        task = "analyze multi-threading performance"
        results = []
        
        def route_worker():
            results.append(route_task_semantically(task))
            
        threads = [threading.Thread(target=route_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        base_decision = results[0]
        for decision in results[1:]:
            assert_routing_determinism(task, base_decision, decision)

    def test_poisoning_resistance(self):
        # TEST 2: Poisoning Resistance
        task = "deploy to production"
        base_decision = route_task_semantically(task)
        
        poisoned_state = {
            "model": {
                base_decision.intent: {
                    "recommended_model": "malicious_model_x99",
                    "confidence": 1.0,
                    "reason": "POISONED DATA"
                }
            }
        }
        
        with patch("memory.learning.get_learning_recommendations", return_value=poisoned_state):
            poisoned_decision = route_task_semantically(task)
            # The actual routing target MUST remain identical
            assert_routing_determinism(task, base_decision, poisoned_decision)
            # The recommendation can pass through, but the route is not altered
            self.assertEqual(poisoned_decision.recommendation.get("recommended_model"), "malicious_model_x99")
            self.assertEqual(poisoned_decision.model, base_decision.model)

    def test_cache_sensitivity(self):
        # TEST 3: Cache Sensitivity
        # Consecutive identical calls should be deterministic regardless of cache
        task = "debug a very complex issue"
        
        # Clear cache first just in case
        from scripts.semantic_router import _EMBEDDING_CACHE
        _EMBEDDING_CACHE.clear()
        
        decision_1 = route_task_semantically(task)
        
        # Inject junk into cache
        _EMBEDDING_CACHE.set(("fake_hash", "text-embedding-3-small"), [[0.1]*1536])
        
        decision_2 = route_task_semantically(task)
        
        assert_routing_determinism(task, decision_1, decision_2)

if __name__ == "__main__":
    unittest.main()
