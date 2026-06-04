import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import create_default_registry
from workflows.engine import WorkflowEngine


class SyncMasterToolsTests(unittest.TestCase):
    def test_registry_contains_syncmaster_tools(self):
        registry = create_default_registry()
        names = registry.names()

        self.assertIn("syncmaster_analyze_metadata", names)
        self.assertIn("syncmaster_analyze_audio", names)
        self.assertIn("syncmaster_recommend_sync_fit", names)
        self.assertIn("syncmaster_match_brief", names)
        self.assertIn("syncmaster_save_track", names)
        self.assertIn("syncmaster_save_brief", names)
        self.assertIn("syncmaster_save_recommendation", names)

    def test_metadata_and_recommendation_tools_execute(self):
        registry = create_default_registry()

        metadata = registry.execute(
            "syncmaster_analyze_metadata",
            {"payload": {"description": "Dark cinematic 120 bpm instrumental strings", "genre": ["cinematic"]}},
        )
        recommendation = registry.execute(
            "syncmaster_recommend_sync_fit",
            {
                "track_metadata": metadata["metadata"],
                "brief": {"genres": ["cinematic"], "moods": ["dark"], "min_bpm": 110, "max_bpm": 125},
            },
        )

        self.assertEqual(metadata["metadata"]["bpm"], 120)
        self.assertIn("fit_score", recommendation)

    def test_workflow_chains_metadata_to_recommendation_and_persists_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = str(Path(temp_dir) / "graph.json")
            registry = create_default_registry()
            engine = WorkflowEngine(registry)

            with patch("memory.graph.GRAPH_FILE", graph_path):
                outputs = engine.execute(
                    [
                        {
                            "id": "metadata",
                            "tool": "syncmaster_analyze_metadata",
                            "args": {
                                "payload": {
                                    "title": "Night Lift",
                                    "description": "Dark cinematic 118 bpm instrumental strings",
                                }
                            },
                        },
                        {
                            "id": "recommend",
                            "tool": "syncmaster_recommend_sync_fit",
                            "depends_on": ["metadata"],
                            "args": {
                                "track_metadata": {"$from": "metadata", "path": "metadata"},
                                "brief": {"genres": ["cinematic"], "moods": ["dark"], "min_bpm": 110, "max_bpm": 124},
                            },
                        },
                        {
                            "id": "save_track",
                            "tool": "syncmaster_save_track",
                            "depends_on": ["metadata"],
                            "args": {
                                "track": {"$from": "metadata", "path": "metadata"},
                                "track_id": "night_lift",
                            },
                        },
                    ]
                )

            self.assertIn("fit_score", outputs["recommend"])
            self.assertEqual(outputs["save_track"]["id"], "track:night_lift")


if __name__ == "__main__":
    unittest.main()
