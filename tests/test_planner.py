import unittest
from unittest.mock import patch

from planning import (
    ClaudePlanningProvider,
    DeterministicPlanningProvider,
    Plan,
    PlanStep,
    PlanValidationError,
    select_planning_provider,
    validate_plan,
)


class PlannerTests(unittest.TestCase):
    def test_deterministic_provider_returns_valid_plan(self):
        provider = DeterministicPlanningProvider()

        plan = provider.create_plan("debug the Python API tests", max_steps=4)

        self.assertEqual(plan.provider, "deterministic")
        self.assertEqual(plan.objective, "debug the Python API tests")
        self.assertEqual(plan.steps[1].tool_name, "code_agent")
        self.assertEqual(plan.steps[1].dependencies, ["step_1"])

    def test_validation_rejects_too_many_steps(self):
        plan = Plan(
            id="plan_many",
            objective="too many",
            steps=[
                PlanStep(id="step_1", description="one", tool_name="local_model"),
                PlanStep(id="step_2", description="two", tool_name="local_model"),
            ],
        )

        with self.assertRaisesRegex(PlanValidationError, "max steps"):
            validate_plan(plan, max_steps=1)

    def test_validation_rejects_duplicate_step_ids(self):
        plan = Plan(
            id="plan_duplicate",
            objective="duplicate",
            steps=[
                PlanStep(id="step_1", description="one", tool_name="local_model"),
                PlanStep(id="step_1", description="two", tool_name="local_model"),
            ],
        )

        with self.assertRaisesRegex(PlanValidationError, "unique"):
            validate_plan(plan)

    def test_validation_rejects_unknown_dependency(self):
        plan = Plan(
            id="plan_dependency",
            objective="dependency",
            steps=[
                PlanStep(
                    id="step_1",
                    description="one",
                    tool_name="local_model",
                    dependencies=["missing"],
                )
            ],
        )

        with self.assertRaisesRegex(PlanValidationError, "unknown step"):
            validate_plan(plan)

    def test_validation_rejects_cycles(self):
        plan = Plan(
            id="plan_cycle",
            objective="cycle",
            steps=[
                PlanStep(
                    id="step_1",
                    description="one",
                    tool_name="local_model",
                    dependencies=["step_2"],
                ),
                PlanStep(
                    id="step_2",
                    description="two",
                    tool_name="local_model",
                    dependencies=["step_1"],
                ),
            ],
        )

        with self.assertRaisesRegex(PlanValidationError, "cycle"):
            validate_plan(plan)

    def test_validation_rejects_invalid_tool_name(self):
        plan = Plan(
            id="plan_tool",
            objective="tool",
            steps=[
                PlanStep(id="step_1", description="one", tool_name="shell"),
            ],
        )

        with self.assertRaisesRegex(PlanValidationError, "invalid tool"):
            validate_plan(plan)

    def test_deterministic_provider_selects_syncmaster_metadata_tool(self):
        provider = DeterministicPlanningProvider()

        plan = provider.create_plan("analyze BPM key mood and genre metadata", max_steps=4)

        self.assertEqual(plan.steps[1].tool_name, "syncmaster_analyze_metadata")
        self.assertIn("payload", plan.steps[1].inputs)

    def test_deterministic_provider_selects_syncmaster_licensing_tool(self):
        provider = DeterministicPlanningProvider()

        plan = provider.create_plan("recommend sync licensing fit for an ad brief", max_steps=4)

        self.assertEqual(plan.steps[1].tool_name, "syncmaster_recommend_sync_fit")
        self.assertIn("track_metadata", plan.steps[1].inputs)
        self.assertIn("brief", plan.steps[1].inputs)

    def test_auto_provider_falls_back_to_deterministic_without_api_key(self):
        with patch.dict("os.environ", {"PLANNING_PROVIDER": "auto"}, clear=True):
            provider = select_planning_provider()

        self.assertIsInstance(provider, DeterministicPlanningProvider)

    def test_explicit_claude_provider_interface_does_not_call_api_until_create(self):
        provider = ClaudePlanningProvider(client=None, api_key=None)

        self.assertFalse(provider.is_available())

    def test_claude_provider_can_validate_client_response_without_real_api(self):
        class FakeMessages:
            def create(self, **kwargs):
                return type(
                    "Message",
                    (),
                    {
                        "content": [
                            type(
                                "Content",
                                (),
                                {
                                    "text": """{
                                        "id": "plan_fake",
                                        "objective": "fake task",
                                        "provider": "claude",
                                        "steps": [
                                            {
                                                "id": "step_1",
                                                "description": "do it",
                                                "tool_name": "local_model",
                                                "dependencies": [],
                                                "inputs": {}
                                            }
                                        ]
                                    }"""
                                },
                            )()
                        ]
                    },
                )()

        class FakeClient:
            messages = FakeMessages()

        provider = ClaudePlanningProvider(client=FakeClient())

        plan = provider.create_plan("fake task")

        self.assertEqual(plan.provider, "claude")
        self.assertEqual(plan.steps[0].tool_name, "local_model")


if __name__ == "__main__":
    unittest.main()
