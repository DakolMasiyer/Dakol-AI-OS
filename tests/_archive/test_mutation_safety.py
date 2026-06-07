import unittest
from unittest.mock import patch
from scripts.semantic_router import route_task_semantically
from agents.orchestrator import Orchestrator

class MutationSafetyTests(unittest.TestCase):
    
    def test_routing_immutability(self):
        # TEST 1 — ROUTING IMMUTABILITY:
        # Generate learning state with a strong bias to route software_engineering tasks to claude
        strong_bias_state = {
            "recommendations": {
                "model": {
                    "software_engineering": {
                        "recommended_model": "claude",
                        "confidence": 0.99,
                        "reason": "Force Claude route preference"
                    }
                },
                "agent": {},
                "confidence": {}
            },
            "analytics": {
                "version": 1,
                "updated_at": "2026-06-07T12:00:00",
                "event_count": 10,
                "intents": {
                    "software_engineering": {
                        "count": 5
                    }
                },
                "models": {},
                "agents": {},
                "low_confidence_patterns": []
            }
        }
        
        with patch("memory.learning.load_learning_state", return_value=strong_bias_state):
            # Run router 100 times and assert model selection never changes
            for _ in range(100):
                decision = route_task_semantically("write python code and implement a FastAPI server")
                self.assertEqual(decision.model, "codex")
                self.assertEqual(decision.recommendation["recommended_model"], "claude")
                self.assertEqual(decision.recommendation["confidence"], 0.99)
                self.assertFalse(decision.learning_applied)
                
    def test_agent_weight_immutability(self):
        # TEST 2 — AGENT WEIGHT IMMUTABILITY:
        # Set extreme multipliers in learning_state
        extreme_state = {
            "recommendations": {
                "agent": {
                    "sync_agent": {
                        "recommended_multiplier": 500.0,
                        "confidence": 0.99,
                        "reason": "Extremely strong positive bias"
                    },
                    "audio_agent": {
                        "recommended_multiplier": 0.001,
                        "confidence": 0.99,
                        "reason": "Extremely strong negative bias"
                    }
                }
            },
            "analytics": {
                "agents": {
                    "sync_agent": {
                        "count": 5
                    },
                    "audio_agent": {
                        "count": 5
                    }
                }
            }
        }
        
        with patch("memory.learning.load_learning_state", return_value=extreme_state):
            orchestrator = Orchestrator()
            
            # Assert agent base_weight and domain_weight remain completely unchanged
            agents = {agent.name: agent for agent in orchestrator.agents}
            self.assertEqual(agents["sync_agent"].base_weight, 1.3)
            self.assertEqual(agents["sync_agent"].domain_weight, 1.3)
            self.assertEqual(agents["audio_agent"].base_weight, 1.0)
            self.assertEqual(agents["audio_agent"].domain_weight, 1.0)
            
            # Run orchestrator and verify weights still remain unchanged
            with patch.object(orchestrator, "_run_llm", return_value='{"final_intent": "test", "reasoning": "ok", "best_agent": "sync_agent", "confidence": 0.9}'):
                _ = orchestrator.route("test task")
                
            self.assertEqual(agents["sync_agent"].base_weight, 1.3)
            self.assertEqual(agents["sync_agent"].domain_weight, 1.3)
            self.assertEqual(agents["audio_agent"].base_weight, 1.0)
            self.assertEqual(agents["audio_agent"].domain_weight, 1.0)
            
    def test_restart_consistency(self):
        # TEST 3 — RESTART CONSISTENCY:
        # Restart consistency check: identical inputs yield identical routing output across different bias states
        task = "analyze BPM key and mood tags for this track"
        
        state_a = {
            "recommendations": {
                "model": {
                    "sync_metadata": {
                        "recommended_model": "claude",
                        "confidence": 0.99,
                        "reason": "Recommend Claude"
                    }
                }
            },
            "analytics": {
                "intents": {
                    "sync_metadata": {
                        "count": 5
                    }
                }
            }
        }
        
        state_b = {
            "recommendations": {
                "model": {
                    "sync_metadata": {
                        "recommended_model": "local",
                        "confidence": 0.99,
                        "reason": "Recommend local"
                    }
                }
            },
            "analytics": {
                "intents": {
                    "sync_metadata": {
                        "count": 5
                    }
                }
            }
        }
        
        with patch("memory.learning.load_learning_state", return_value=state_a):
            decision_a = route_task_semantically(task)
            
        with patch("memory.learning.load_learning_state", return_value=state_b):
            decision_b = route_task_semantically(task)
            
        self.assertEqual(decision_a.model, decision_b.model)
        self.assertEqual(decision_a.intent, decision_b.intent)
        self.assertEqual(decision_a.confidence, decision_b.confidence)
        
    def test_mutation_protection(self):
        # TEST 4 — MUTATION PROTECTION:
        # Verify that even when overriding learning_state.json manually to force overrides,
        # the system ignores it and executes the static route.
        override_state = {
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
                        "count": 10
                    }
                }
            }
        }
        
        with patch("memory.learning.load_learning_state", return_value=override_state):
            decision = route_task_semantically("implement backend api script")
            
        # Expectation: model routes statically to codex and ignores the recommendations override
        self.assertEqual(decision.model, "codex")
        self.assertEqual(decision.recommendation["recommended_model"], "local")
        self.assertEqual(decision.recommendation["confidence"], 0.99)
        self.assertFalse(decision.learning_applied)

if __name__ == "__main__":
    unittest.main()
