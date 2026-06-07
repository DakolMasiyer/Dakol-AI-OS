import copy
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from agents.orchestrator import Orchestrator
from core.invariants import ExecutionPathContext, assert_learning_is_advisory_only
from scripts import router
from scripts.semantic_router import RouteDecision, route_task_semantically


class FailureInjectionTests(unittest.TestCase):
    def test_malformed_learning_state_does_not_change_route(self):
        malformed_state = {"recommendations": None, "analytics": "broken"}
        with patch("memory.learning.load_learning_state", return_value=malformed_state):
            decision = route_task_semantically("implement tests for a Python package")

        self.assertEqual(decision.model, "codex")
        self.assertEqual(decision.route, "software_engineering")

    def test_poisoned_recommendations_do_not_change_route(self):
        poisoned_state = {
            "model": {
                "software_engineering": {
                    "recommended_model": "malicious_model",
                    "confidence": 1.0,
                    "reason": "poisoned"
                }
            }
        }
        with patch("memory.learning.get_learning_recommendations", return_value=poisoned_state):
            decision = route_task_semantically("implement tests for a Python package")

        self.assertEqual(decision.model, "codex")
        self.assertEqual(decision.recommendation["recommended_model"], "malicious_model")

    def test_partial_agent_failure_is_graceful(self):
        with patch.object(
            Orchestrator,
            "_run_llm",
            return_value='{"final_intent":"ok","reasoning":"ok","best_agent":"code_agent","confidence":0.9}',
        ), patch("agents.orchestrator.SyncAgent.run", side_effect=RuntimeError("agent boom")):
            result = Orchestrator().route("debug a Python script")

        failed_agents = [item for item in result["all_results"] if item.get("status") == "failed"]
        self.assertTrue(failed_agents)
        self.assertEqual(failed_agents[0]["agent"], "sync_agent")

    def test_timeout_conditions_fall_back_deterministically(self):
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
            "all_results": [],
            "learning_signals": [],
            "route_decision": fixed_route.to_dict(),
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            trace_dir = Path(temp_dir) / "execution"
            with patch("core.execution_audit.TRACE_DIR", trace_dir), patch(
                "scripts.router.route_task_semantically", return_value=fixed_route
            ), patch("scripts.router.run_codex", side_effect=TimeoutError("timeout")), patch.object(
                Orchestrator,
                "route",
                side_effect=lambda *args, **kwargs: copy.deepcopy(agent_result),
            ):
                result = router.execute_task(
                    "implement tests for a Python package",
                    record_memory=False,
                    record_trace=False,
                    capture_metadata=True,
                )

        self.assertEqual(result["status"], "failed")
        self.assertIn("TimeoutError", result["failure_reason"])
        self.assertIn("timeout", result["output"])

    def test_invalid_invariant_state_is_rejected(self):
        with ExecutionPathContext(), patch("memory.learning.get_learning_recommendations", return_value={}):
            with self.assertRaises(AssertionError):
                assert_learning_is_advisory_only()

    def test_concurrent_execution_pressure_is_stable(self):
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
            "all_results": [],
            "learning_signals": [],
            "route_decision": fixed_route.to_dict(),
        }

        with patch("scripts.router.route_task_semantically", return_value=fixed_route), patch(
            "scripts.router.run_codex", return_value="stable output"
        ), patch.object(Orchestrator, "route", side_effect=lambda *args, **kwargs: copy.deepcopy(agent_result)):
            with ThreadPoolExecutor(max_workers=10) as pool:
                futures = [
                    pool.submit(
                        router.execute_task,
                        "implement tests for a Python package",
                        record_memory=False,
                        record_trace=False,
                        capture_metadata=True,
                    )
                    for _ in range(20)
                ]

            results = [future.result() for future in futures]

        self.assertEqual({result["status"] for result in results}, {"completed"})
        self.assertEqual({result["output"] for result in results}, {"stable output"})


if __name__ == "__main__":
    unittest.main()
