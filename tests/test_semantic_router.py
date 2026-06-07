import unittest
from unittest.mock import patch

from scripts.router import analyze_task
from scripts.semantic_router import route_task_semantically


class SemanticRouterTests(unittest.TestCase):
    def test_routes_code_work_to_codex(self):
        decision = route_task_semantically("create tests and fix the FastAPI integration")

        self.assertEqual(decision.model, "codex")
        self.assertEqual(decision.intent, "software_engineering")
        self.assertGreater(decision.confidence, 0)

    def test_routes_architecture_work_to_claude(self):
        decision = route_task_semantically("plan the agent orchestration roadmap and architecture")

        self.assertEqual(decision.model, "claude")
        self.assertEqual(decision.intent, "system_architecture")
        self.assertGreater(decision.confidence, 0)

    def test_routes_metadata_work_to_local(self):
        decision = route_task_semantically("analyze BPM key mood and genre tags for this song")

        self.assertEqual(decision.model, "local")
        self.assertEqual(decision.intent, "sync_metadata")
        self.assertGreater(decision.confidence, 0)

    def test_public_analyze_task_contract_returns_model(self):
        self.assertEqual(analyze_task("debug this Python script"), "codex")

    def test_embedding_provider_can_select_route(self):
        def fake_provider(texts):
            return [
                [1.0, 0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
            ]

        decision = route_task_semantically(
            "prepare backend validation coverage",
            embedding_provider=fake_provider,
        )

        self.assertEqual(decision.model, "codex")
        self.assertEqual(decision.intent, "software_engineering")
        self.assertEqual(decision.scoring_method, "embedding")

    def test_embedding_provider_failure_falls_back_to_lexical(self):
        def failing_provider(texts):
            raise TimeoutError("embedding timeout")

        decision = route_task_semantically(
            "plan the orchestration architecture",
            embedding_provider=failing_provider,
        )

        self.assertEqual(decision.model, "claude")
        self.assertEqual(decision.intent, "system_architecture")
        self.assertEqual(decision.scoring_method, "lexical")

    def test_invalid_embedding_output_falls_back_to_lexical(self):
        def invalid_provider(texts):
            return [[1.0, 0.0]]

        decision = route_task_semantically(
            "analyze BPM key mood genre tags",
            embedding_provider=invalid_provider,
        )

        self.assertEqual(decision.model, "local")
        self.assertEqual(decision.intent, "sync_metadata")
        self.assertEqual(decision.scoring_method, "lexical")

    def test_low_confidence_embedding_does_not_override_lexical(self):
        def weak_provider(texts):
            return [[0.0, 0.0] for _ in texts]

        decision = route_task_semantically(
            "analyze BPM key mood genre tags",
            embedding_provider=weak_provider,
        )

        self.assertEqual(decision.model, "local")
        self.assertEqual(decision.intent, "sync_metadata")
        self.assertEqual(decision.scoring_method, "lexical")

    def test_public_contract_remains_model_string_with_embeddings_enabled(self):
        with patch.dict("os.environ", {"SEMANTIC_ROUTER_EMBEDDINGS": "none"}):
            self.assertIn(analyze_task("debug this Python script"), {"claude", "codex", "local"})

if __name__ == "__main__":
    unittest.main()
