import unittest
from pathlib import Path

from scripts.import_graph_snapshot import build_import_graph, load_snapshot, validate_snapshot


class ImportGraphStabilityTests(unittest.TestCase):
    def test_import_graph_matches_frozen_snapshot(self):
        repo_root = Path(__file__).resolve().parents[1]
        snapshot_path = repo_root / "artifacts" / "import_graph_snapshot.json"

        snapshot = load_snapshot(snapshot_path)
        current = build_import_graph(repo_root)
        issues = validate_snapshot(snapshot, current)

        self.assertEqual(issues, [])
        self.assertEqual(snapshot["fingerprint"], current["fingerprint"])
        self.assertEqual(snapshot["forbidden_learning_imports"], [])


if __name__ == "__main__":
    unittest.main()
