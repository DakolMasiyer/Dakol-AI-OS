import unittest
from unittest.mock import patch, MagicMock

from agents.orchestrator import Orchestrator


class OrchestratorLearningTests(unittest.TestCase):
    def test_default_learning_state_preserves_agent_weights(self):
        orchestrator = Orchestrator(
            learning_state={
                "agent_bias": {}
            }
        )

        weights = {agent.name: agent.domain_weight for agent in orchestrator.agents}

        self.assertEqual(weights["sync_agent"], 1.3)
        self.assertEqual(weights["audio_agent"], 1.0)
        self.assertEqual(weights["code_agent"], 1.0)

    def test_agent_learning_applies_clamped_multiplier(self):
        orchestrator = Orchestrator(
            learning_state={
                "agent_bias": {
                    "sync_agent": {
                        "weight_multiplier": 1.2,
                        "sample_size": 3,
                    },
                    "audio_agent": {
                        "weight_multiplier": 0.5,
                        "sample_size": 3,
                    },
                }
            }
        )
        agents = {agent.name: agent for agent in orchestrator.agents}

        self.assertEqual(agents["sync_agent"].base_domain_weight, 1.3)
        self.assertEqual(agents["sync_agent"].learning_multiplier, 1.2)
        self.assertEqual(agents["sync_agent"].domain_weight, 1.56)
        self.assertEqual(agents["audio_agent"].learning_multiplier, 0.75)
        self.assertEqual(agents["audio_agent"].domain_weight, 0.75)
        self.assertEqual(agents["code_agent"].learning_multiplier, 1.0)
        self.assertEqual(agents["code_agent"].domain_weight, 1.0)


    def test_run_llm_returns_json_payload(self):
        orch = Orchestrator(learning_state={"agent_bias": {}})
        mock_response = MagicMock()
        mock_response.text = '{"final_intent": "test", "reasoning": "ok", "best_agent": "sync_agent", "confidence": 0.9}'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        with patch("google.genai.Client", return_value=mock_client):
            result = orch._run_llm("test prompt")
        assert "final_intent" in result
        assert result


if __name__ == "__main__":
    unittest.main()
