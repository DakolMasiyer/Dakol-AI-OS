import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from memory.log import VALID_FEEDBACK, log_event, record_feedback
from scripts import memory as script_memory


class MemoryLogTests(unittest.TestCase):
    def test_log_event_persists_stable_event_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"

            with patch("memory.log.MEMORY_FILE", str(logs_path)):
                with redirect_stdout(StringIO()):
                    entry = log_event("route this task", "codex", "ok")

            saved = json.loads(logs_path.read_text())

            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["event_id"], entry["event_id"])
            self.assertIsInstance(entry["event_id"], str)
            self.assertTrue(entry["event_id"])

    def test_log_event_accepts_none_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"

            with patch("memory.log.MEMORY_FILE", str(logs_path)):
                with redirect_stdout(StringIO()):
                    entry = log_event("route this task", "codex", None)

            self.assertEqual(entry["output"], "")

    def test_record_feedback_accepts_required_values(self):
        self.assertEqual(VALID_FEEDBACK, {"good", "bad", "wrong_model", "retry_needed"})

        for feedback in VALID_FEEDBACK:
            with self.subTest(feedback=feedback):
                with tempfile.TemporaryDirectory() as temp_dir:
                    logs_path = Path(temp_dir) / "logs.json"

                    with patch("memory.log.MEMORY_FILE", str(logs_path)):
                        with redirect_stdout(StringIO()):
                            entry = log_event("route this task", "local", "ok")
                        updated = record_feedback(entry["event_id"], feedback, note="useful note")

                    saved = json.loads(logs_path.read_text())

                    self.assertEqual(updated["feedback"]["value"], feedback)
                    self.assertEqual(updated["feedback"]["label"], feedback)
                    self.assertEqual(saved[0]["feedback"]["value"], feedback)
                    self.assertEqual(saved[0]["feedback"]["label"], feedback)
                    self.assertEqual(saved[0]["feedback"]["note"], "useful note")

    def test_record_feedback_rejects_unknown_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"

            with patch("memory.log.MEMORY_FILE", str(logs_path)):
                with redirect_stdout(StringIO()):
                    entry = log_event("route this task", "local", "ok")

                with self.assertRaises(ValueError):
                    record_feedback(entry["event_id"], "maybe")

    def test_record_feedback_rejects_missing_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"
            logs_path.write_text("[]")

            with patch("memory.log.MEMORY_FILE", str(logs_path)):
                with self.assertRaises(ValueError):
                    record_feedback("missing", "bad")

    def test_script_memory_uses_canonical_logger(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"
            original_memory_file = script_memory.MEMORY_FILE

            script_memory.MEMORY_FILE = str(logs_path)
            try:
                with redirect_stdout(StringIO()):
                    entry = script_memory.log_event("old import", "local", "ok")
            finally:
                script_memory.MEMORY_FILE = original_memory_file

            self.assertIn("event_id", entry)
            self.assertIn("agent_result", entry)


if __name__ == "__main__":
    unittest.main()
