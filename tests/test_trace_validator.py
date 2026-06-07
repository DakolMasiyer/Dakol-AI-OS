import tempfile
import unittest
from pathlib import Path

from core.execution_audit import create_execution_snapshot, write_execution_trace
from scripts.validate_traces import validate_trace_data, validate_trace_file


class TraceValidatorTests(unittest.TestCase):
    def test_valid_trace_passes_schema_validation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            trace_dir = Path(temp_dir)
            snapshot = create_execution_snapshot(
                execution_id="exec-1",
                task="write tests",
                input_payload={"task": "write tests"},
                route_decision={
                    "model": "codex",
                    "intent": "software_engineering",
                    "confidence": 0.9,
                    "matched_terms": ["tests"],
                    "route": "software_engineering",
                    "execution_target": "codex",
                    "scoring_method": "lexical",
                    "embedding_provider": "",
                    "learning_applied": False,
                },
                selected_model="codex",
                selected_agent="code_agent",
                execution_timestamps={
                    "started_at": "2026-06-07T12:00:00+00:00",
                    "finished_at": "2026-06-07T12:00:01+00:00",
                    "duration_ms": 1000,
                },
                invariant_checks={
                    "routing_determinism": True,
                    "agent_immutability": True,
                    "learning_is_advisory_only": True,
                },
                output="ok",
                agent_result={"fusion_output": {"best_agent": "code_agent"}},
                status="completed",
                request_id="req-1",
                workflow_id="work-1",
                best_agent="code_agent",
            )
            trace_path = write_execution_trace(snapshot, trace_dir=trace_dir)

            issues = validate_trace_file(trace_path)
            self.assertEqual(issues, [])

    def test_malformed_trace_is_rejected(self):
        malformed = {
            "schema_version": 1,
            "execution_id": "exec-2",
            "task": "write tests",
            "input_payload": {"task": "write tests"},
            "route_decision": {},
            "selected_model": "codex",
            "selected_agent": "code_agent",
            "execution_timestamps": {"started_at": "now"},
            "invariant_checks": {"routing_determinism": "yes"},
            "output_hash": "not-a-sha256",
            "route_fingerprint": "123",
            "invariant_fingerprint": "456",
            "execution_result_hash": "789",
            "execution_fingerprint": "abc",
            "status": "completed",
        }

        issues = validate_trace_data(malformed)
        self.assertGreaterEqual(len(issues), 5)


if __name__ == "__main__":
    unittest.main()
