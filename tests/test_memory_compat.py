import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from memory import log as canonical_memory
from scripts import memory as legacy_memory


class MemoryCompatTests(unittest.TestCase):
    def test_legacy_logger_delegates_to_canonical_agent_result_shape(self):
        original_memory_file = legacy_memory.MEMORY_FILE

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"
            logs_path.write_text("[]")
            legacy_memory.MEMORY_FILE = str(logs_path)

            try:
                with redirect_stdout(io.StringIO()):
                    entry = legacy_memory.log_event(
                        "tag this track",
                        "local",
                        "ok",
                        {
                            "fusion_output": {
                                "final_intent": "sync_metadata",
                                "best_agent": "sync_agent",
                                "confidence": 0.8,
                            }
                        },
                    )
            finally:
                legacy_memory.MEMORY_FILE = original_memory_file

            stored = json.loads(logs_path.read_text())

        self.assertEqual(entry["agent_result"]["fusion_output"]["best_agent"], "sync_agent")
        self.assertEqual(stored[0]["agent_result"]["fusion_output"]["final_intent"], "sync_metadata")

    def test_legacy_memory_file_override_applies_to_load_and_save(self):
        original_memory_file = legacy_memory.MEMORY_FILE
        original_canonical_memory_file = canonical_memory.MEMORY_FILE

        with tempfile.TemporaryDirectory() as temp_dir:
            logs_path = Path(temp_dir) / "logs.json"
            legacy_memory.MEMORY_FILE = str(logs_path)

            try:
                legacy_memory.save_memory([{"task": "saved through legacy path"}])
                loaded = legacy_memory.load_memory()
            finally:
                legacy_memory.MEMORY_FILE = original_memory_file

        self.assertEqual(loaded, [{"task": "saved through legacy path"}])
        self.assertEqual(canonical_memory.MEMORY_FILE, original_canonical_memory_file)


if __name__ == "__main__":
    unittest.main()
