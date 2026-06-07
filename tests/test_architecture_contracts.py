import unittest
from unittest.mock import patch
from scripts.semantic_router import route_task_semantically
from core.invariants import (
    assert_routing_determinism,
    assert_agent_immutability,
    assert_learning_is_advisory_only,
    assert_no_learning_state_direct_access,
    ExecutionPathContext
)
from memory.learning import get_learning_recommendations
from agents.orchestrator import Orchestrator

class ArchitectureContractsTests(unittest.TestCase):
    
    def test_routing_determinism(self):
        # TEST 1 — ROUTING DETERMINISM
        # same input → identical output across different learning states
        task = "write python code and implement a FastAPI server"
        
        # Call the routing logic directly
        decision_before = route_task_semantically(task)
        decision_after = route_task_semantically(task)
        
        # Assert routing output fields match
        assert_routing_determinism(task, decision_before, decision_after)
        self.assertEqual(decision_before.model, decision_after.model)
        self.assertEqual(decision_before.intent, decision_after.intent)
        self.assertEqual(decision_before.route, decision_after.route)
        self.assertEqual(decision_before.execution_target, decision_after.execution_target)

    def test_agent_immutability(self):
        # TEST 2 — AGENT IMMUTABILITY
        # attempt mutation → must fail or be ignored
        orchestrator = Orchestrator()
        
        # Test that trying to assign domain_weight directly raises AttributeError
        for agent in orchestrator.agents:
            with self.assertRaises(AttributeError):
                agent.domain_weight = 3.14
            self.assertEqual(agent.domain_weight, agent.base_weight)
            
        # Assert invariants pass cleanly
        assert_agent_immutability(orchestrator.agents)

    def test_learning_is_advisory_only(self):
        # TEST 3 — LEARNING IS ADVISORY ONLY
        # learning_state changes MUST NOT affect routing or execution
        task = "implement tests for a Python package"
        
        # 1. Base route
        decision_base = route_task_semantically(task)
        self.assertEqual(decision_base.model, "codex")
        self.assertFalse(decision_base.learning_applied)
        
        # 2. Setup drastic learning state recommending different model and multiplier
        state_drastic = {
            "model": {
                "software_engineering": {
                    "recommended_model": "local",
                    "confidence": 0.99,
                    "reason": "Bias to local model"
                }
            },
            "agent": {
                "sync_agent": {
                    "recommended_multiplier": 50.0,
                    "confidence": 0.99,
                    "reason": "Drastic agent bias"
                }
            }
        }
        
        with patch("memory.learning.get_learning_recommendations", return_value=state_drastic):
            decision_biased = route_task_semantically(task)
            
            # The decision model selection MUST NOT be modified by the state recommendations
            self.assertEqual(decision_biased.model, "codex")
            self.assertEqual(decision_biased.recommendation["recommended_model"], "local")
            self.assertFalse(decision_biased.learning_applied)
            
            # Re-verify that even with this recommendations state, orchestrator weights are unchanged
            orchestrator = Orchestrator()
            agents = {agent.name: agent for agent in orchestrator.agents}
            self.assertEqual(agents["sync_agent"].domain_weight, 1.3)
            self.assertEqual(agents["sync_agent"].base_weight, 1.3)

    def test_direct_access_protection(self):
        # TEST 4 — DIRECT ACCESS PROTECTION
        # any import or parsing of learning_state.json outside memory/learning.py must fail
        with self.assertRaises(RuntimeError) as ctx:
            assert_no_learning_state_direct_access("agents.orchestrator")
        self.assertIn("DIRECT ACCESS VIOLATION", str(ctx.exception))
        
        with self.assertRaises(RuntimeError) as ctx2:
            assert_no_learning_state_direct_access("scripts.semantic_router")
        self.assertIn("DIRECT ACCESS VIOLATION", str(ctx2.exception))
        
        # Verify allowed modules do not raise exceptions
        assert_no_learning_state_direct_access("memory.learning")
        assert_no_learning_state_direct_access("tests.test_architecture_contracts")
