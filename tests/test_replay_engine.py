import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.orchestrator import Orchestrator
from core.execution_audit import load_execution_trace, verify_replay
from scripts import replay_execution
from scripts.semantic_router import RouteDecision
from scripts import router


class ReplayEngineTests(unittest.TestCase):
    def test_hundred_identical_replays_share_the_same_execution_fingerprint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_dir = Path(temp_dir) / "execution"
            fixed_route = RouteDecision(
                model="codex",
                intent="software_engineering",
                confidence=0.91,
                matched_terms=["code"],
                route="software_engineering",
                execution_target="codex",
            )
            agent_result = {
                "fusion_output": {
                    "best_agent": "code_agent",
                    "final_intent": "software_engineering",
                    "confidence": 0.91,
                },
                "all_results": [
                    {"agent": "code_agent", "intent": "software_engineering", "confidence": 0.9, "status": "processed"}
                ],
                "learning_signals": [],
                "route_decision": fixed_route.to_dict(),
            }

            with patch("core.execution_audit.TRACE_DIR", trace_dir), patch(
                "scripts.router.route_task_semantically", return_value=fixed_route
            ), patch(
                "scripts.router.run_codex", return_value="deterministic output"
            ), patch.object(
                Orchestrator,
                "route",
                side_effect=lambda *args, **kwargs: copy.deepcopy(agent_result),
            ):
                replay_results = []
                for _ in range(100):
                    result = router.execute_task(
                        "implement tests for a Python package",
                        record_memory=False,
                        record_trace=True,
                        capture_metadata=True,
                    )
                    replay_results.append(result)

                traces = sorted(trace_dir.glob("*.json"))
                self.assertEqual(len(traces), 100)

                fingerprints = set()
                for trace_path in traces:
                    snapshot = load_execution_trace(trace_path)
                    fingerprints.add(snapshot.execution_fingerprint)
                    verification = verify_replay(snapshot, replay_results[0])
                    self.assertEqual(verification["status"], "VERIFIED")

                self.assertEqual(len(fingerprints), 1)

                replay_verdict = replay_execution.replay_trace(traces[0], repeat=3)
                self.assertEqual(replay_verdict["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
