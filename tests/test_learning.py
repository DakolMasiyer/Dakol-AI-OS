import json
import tempfile
import unittest
from pathlib import Path

from memory.learning import (
    analyze_logs,
    get_agent_weight_multiplier,
    get_model_bias_for_intent,
    load_learning_state,
    score_event,
    update_learning_state,
)


class LearningTests(unittest.TestCase):
    def test_score_event_handles_legacy_log_entry(self):
        event = score_event(
            {
                "timestamp": "2026-01-01T00:00:00",
                "task": "legacy task",
                "model_used": "local",
                "output": "plain output",
            }
        )

        self.assertEqual(event["intent"], "unknown")
        self.assertEqual(event["model_used"], "local")
        self.assertFalse(event["has_error"])
        self.assertGreater(event["score"], 0)

    def test_score_event_penalizes_errors(self):
        event = score_event(
            {
                "task": "broken task",
                "model_used": "local",
                "output": "Error: model failed",
                "agent_result": {
                    "route_decision": {"intent": "sync_metadata", "confidence": 0.9},
                    "fusion_output": {"confidence": 0.8, "best_agent": "sync_agent"},
                },
            }
        )

        self.assertTrue(event["has_error"])
        self.assertLess(event["score"], 0.5)

    def test_score_event_applies_positive_feedback(self):
        neutral_event = score_event(
            {
                "task": "tag track",
                "model_used": "local",
                "output": "ok",
                "agent_result": {
                    "route_decision": {"intent": "sync_metadata", "confidence": 0.7},
                },
            }
        )
        good_event = score_event(
            {
                "task": "tag track",
                "model_used": "local",
                "output": "ok",
                "feedback": {"label": "good"},
                "agent_result": {
                    "route_decision": {"intent": "sync_metadata", "confidence": 0.7},
                },
            }
        )

        self.assertEqual(good_event["feedback"], "good")
        self.assertGreater(good_event["score"], neutral_event["score"])

    def test_score_event_applies_negative_feedback(self):
        event = score_event(
            {
                "task": "tag track",
                "model_used": "local",
                "output": "ok",
                "feedback": {"label": "wrong_model"},
                "agent_result": {
                    "route_decision": {"intent": "sync_metadata", "confidence": 0.9},
                    "fusion_output": {"confidence": 0.9, "best_agent": "sync_agent"},
                },
            }
        )

        self.assertEqual(event["feedback"], "wrong_model")
        self.assertLess(event["score"], 0.5)

    def test_analyze_logs_builds_model_bias(self):
        state = analyze_logs(
            [
                {
                    "task": "tag a track",
                    "model_used": "local",
                    "output": "ok",
                    "agent_result": {
                        "route_decision": {"intent": "sync_metadata", "confidence": 0.8},
                        "fusion_output": {"confidence": 0.8, "best_agent": "sync_agent"},
                    },
                },
                {
                    "task": "build endpoint",
                    "model_used": "codex",
                    "output": "ok",
                    "agent_result": {
                        "route_decision": {"intent": "software_engineering", "confidence": 0.7},
                        "fusion_output": {"confidence": 0.7, "best_agent": "code_agent"},
                    },
                },
            ]
        )

        self.assertEqual(state["event_count"], 2)
        self.assertEqual(state["model_bias"]["sync_metadata"]["preferred_model"], "local")
        self.assertEqual(state["model_bias"]["software_engineering"]["preferred_model"], "codex")

    def test_analyze_logs_uses_feedback_for_model_bias(self):
        state = analyze_logs(
            [
                {
                    "task": "tag a track",
                    "model_used": "local",
                    "output": "ok",
                    "feedback": {"label": "wrong_model"},
                    "agent_result": {
                        "route_decision": {"intent": "sync_metadata", "confidence": 0.9},
                    },
                },
                {
                    "task": "tag a track",
                    "model_used": "codex",
                    "output": "ok",
                    "feedback": {"label": "good"},
                    "agent_result": {
                        "route_decision": {"intent": "sync_metadata", "confidence": 0.7},
                    },
                },
            ]
        )

        self.assertEqual(state["model_bias"]["sync_metadata"]["preferred_model"], "codex")
        self.assertEqual(state["model_bias"]["sync_metadata"]["sample_size"], 1)

    def test_update_learning_state_handles_missing_log_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "learning_state.json"
            state = update_learning_state(
                logs_path=str(Path(temp_dir) / "missing.json"),
                state_path=str(state_path),
            )

            self.assertEqual(state["event_count"], 0)
            self.assertTrue(state_path.exists())

    def test_load_learning_state_handles_malformed_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "learning_state.json"
            state_path.write_text("{bad json")

            state = load_learning_state(str(state_path))

            self.assertEqual(state["event_count"], 0)

    def test_load_learning_state_reads_valid_state_dict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "learning_state.json"
            state_path.write_text(json.dumps({"event_count": 3, "model_bias": {}}))

            state = load_learning_state(str(state_path))

            self.assertEqual(state["event_count"], 3)

    def test_get_model_bias_for_intent(self):
        state = {
            "model_bias": {
                "sync_metadata": {
                    "preferred_model": "local",
                    "confidence": 0.8,
                    "sample_size": 3,
                }
            }
        }

        self.assertEqual(get_model_bias_for_intent("sync_metadata", state)["preferred_model"], "local")
        self.assertEqual(get_model_bias_for_intent("unknown", state), {})

    def test_agent_weight_multiplier_requires_enough_samples(self):
        state = {
            "agent_bias": {
                "sync_agent": {
                    "weight_multiplier": 1.2,
                    "sample_size": 2,
                }
            }
        }

        self.assertEqual(get_agent_weight_multiplier("sync_agent", state), 1.0)

    def test_agent_weight_multiplier_clamps_values(self):
        high_state = {
            "agent_bias": {
                "sync_agent": {
                    "weight_multiplier": 2.0,
                    "sample_size": 3,
                }
            }
        }
        low_state = {
            "agent_bias": {
                "sync_agent": {
                    "weight_multiplier": 0.1,
                    "sample_size": 3,
                }
            }
        }

        self.assertEqual(get_agent_weight_multiplier("sync_agent", high_state), 1.35)
        self.assertEqual(get_agent_weight_multiplier("sync_agent", low_state), 0.75)

    def test_update_learning_state_reads_log_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"
            state_path = Path(temp_dir) / "learning_state.json"
            logs_path.write_text(
                json.dumps(
                    [
                        {
                            "task": "plan architecture",
                            "model_used": "claude",
                            "output": "ok",
                            "agent_result": {
                                "route_decision": {
                                    "intent": "system_architecture",
                                    "confidence": 0.9,
                                },
                                "fusion_output": {
                                    "confidence": 0.9,
                                    "best_agent": "code_agent",
                                },
                            },
                        }
                    ]
                )
            )

            state = update_learning_state(str(logs_path), str(state_path))

            self.assertEqual(state["event_count"], 1)
            self.assertEqual(state["model_bias"]["system_architecture"]["preferred_model"], "claude")


if __name__ == "__main__":
    unittest.main()
