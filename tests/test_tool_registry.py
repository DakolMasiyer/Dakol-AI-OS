import tempfile
import unittest
from pathlib import Path

from tools import create_default_registry
from tools.registry import ToolRegistry, ToolRegistryError, ToolValidationError


class ToolRegistryTests(unittest.TestCase):
    def test_default_registry_contains_safe_builtins(self):
        registry = create_default_registry()

        names = registry.names()

        self.assertIn("read_file", names)
        self.assertIn("list_files", names)
        self.assertIn("search_repo", names)
        self.assertIn("route_task", names)
        self.assertIn("memory", names)
        self.assertIn("record_feedback", names)
        self.assertNotIn("run_command", names)

    def test_tool_schema_rejects_missing_required_argument(self):
        registry = create_default_registry()

        with self.assertRaises(ToolValidationError):
            registry.execute("read_file", {})

    def test_registry_rejects_unknown_tool(self):
        registry = ToolRegistry()

        with self.assertRaises(ToolRegistryError):
            registry.execute("run_command", {})

    def test_file_tools_are_scoped_to_repo_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "notes.txt").write_text("alpha\nbeta\n")
            registry = create_default_registry(root)

            read_result = registry.execute("read_file", {"path": "notes.txt"})
            list_result = registry.execute("list_files", {"path": "."})
            search_result = registry.execute("search_repo", {"query": "beta"})

            self.assertEqual(read_result["content"], "alpha\nbeta\n")
            self.assertIn("notes.txt", list_result["files"])
            self.assertEqual(search_result["matches"][0]["line_number"], 2)

            with self.assertRaises(ToolValidationError):
                registry.execute("read_file", {"path": "../outside.txt"})

    def test_route_task_returns_structured_decision_without_model_execution(self):
        registry = create_default_registry()

        result = registry.execute("route_task", {"task": "debug this Python script"})

        self.assertIn(result["model"], {"claude", "codex", "local"})
        self.assertIn("intent", result)


if __name__ == "__main__":
    unittest.main()
