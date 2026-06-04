import unittest

from tools.registry import ToolRegistry
from workflows.engine import WorkflowEngine, WorkflowEngineError


class WorkflowEngineTests(unittest.TestCase):
    def make_registry(self):
        registry = ToolRegistry()
        registry.register_function(
            "echo",
            "Return a value.",
            lambda value: {"value": value},
            {
                "type": "object",
                "required": ["value"],
                "additionalProperties": False,
                "properties": {"value": {"type": "string"}},
            },
        )
        registry.register_function(
            "join",
            "Join two values.",
            lambda left, right: {"value": f"{left}:{right}"},
            {
                "type": "object",
                "required": ["left", "right"],
                "additionalProperties": False,
                "properties": {
                    "left": {"type": "string"},
                    "right": {"type": "string"},
                },
            },
        )
        return registry

    def test_executes_steps_in_dependency_order_and_passes_outputs(self):
        engine = WorkflowEngine(self.make_registry())

        outputs = engine.execute(
            [
                {"id": "second", "tool": "join", "depends_on": ["first"], "args": {
                    "left": {"$from": "first", "path": "value"},
                    "right": "done",
                }},
                {"id": "first", "tool": "echo", "args": {"value": "start"}},
            ]
        )

        self.assertEqual(outputs["first"]["value"], "start")
        self.assertEqual(outputs["second"]["value"], "start:done")

    def test_template_references_create_dependencies(self):
        engine = WorkflowEngine(self.make_registry())

        outputs = engine.execute(
            [
                {"id": "summary", "tool": "echo", "args": {"value": "{{seed.value}} ready"}},
                {"id": "seed", "tool": "echo", "args": {"value": "workflow"}},
            ]
        )

        self.assertEqual(outputs["summary"]["value"], "workflow ready")

    def test_rejects_unknown_tool(self):
        engine = WorkflowEngine(self.make_registry())

        with self.assertRaises(WorkflowEngineError):
            engine.execute([{"id": "bad", "tool": "run_command", "args": {}}])

    def test_rejects_dependency_cycles(self):
        engine = WorkflowEngine(self.make_registry())

        with self.assertRaises(WorkflowEngineError):
            engine.execute(
                [
                    {"id": "a", "tool": "echo", "depends_on": ["b"], "args": {"value": "a"}},
                    {"id": "b", "tool": "echo", "depends_on": ["a"], "args": {"value": "b"}},
                ]
            )


if __name__ == "__main__":
    unittest.main()
