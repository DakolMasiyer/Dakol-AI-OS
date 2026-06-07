from __future__ import annotations

import unittest
from pathlib import Path

from scripts.import_graph_snapshot import build_import_graph


ROOT = Path(__file__).resolve().parents[1]
CORE_PREFIX = "core/"
PLATFORM_PREFIXES = ("api/", "app/", "scripts/", "tools/", "runtime/", "farm/")
ALLOWED_LEARNING_IMPORTERS = {
    "agents/orchestrator.py",
    "core/invariants.py",
    "memory/learning.py",
    "scripts/semantic_router.py",
}
APPROVED_EXPERIMENTAL_IMPORTS = (
    "core.api",
    "app.core.",
    "agents.",
    "syncmaster.",
    "workflows.",
    "runtime.",
    "tools.",
    "farm.",
)
APPROVED_APP_IMPORTS = (
    "core.api",
    "apps.",
    "typing",
    "dataclasses",
    "abc",
    "pathlib",
    "json",
    "uuid",
)


class LayerBoundaryTests(unittest.TestCase):
    def test_core_and_platform_do_not_import_experimental_or_apps(self):
        graph = build_import_graph(ROOT)
        violations: list[str] = []

        for edge in graph["edges"]:
            source = edge["source"]
            target = edge["target"]

            if source.startswith(CORE_PREFIX) and target.startswith(("experimental", "apps")):
                violations.append(f"{source}:{edge['line']} -> {target}")
                continue

            if source.startswith(PLATFORM_PREFIXES) and target.startswith(("experimental", "apps")):
                violations.append(f"{source}:{edge['line']} -> {target}")

        self.assertEqual(violations, [], msg="Illegal core/platform dependency on experimental/apps:\n" + "\n".join(violations))

    def test_learning_imports_remain_frozen(self):
        graph = build_import_graph(ROOT)
        violations = []

        for edge in graph["edges"]:
            if edge["target"].startswith("memory.learning") and edge["source"] not in ALLOWED_LEARNING_IMPORTERS:
                violations.append(f"{edge['source']}:{edge['line']} -> {edge['target']}")

        self.assertEqual(violations, [], msg="Illegal memory.learning import(s):\n" + "\n".join(violations))

    def test_application_and_experimental_layers_must_use_public_surfaces(self):
        repo_root = ROOT
        violations = []
        for path in list((repo_root / "experimental").rglob("*.py")) + list((repo_root / "apps").rglob("*.py")):
            rel = path.relative_to(repo_root).as_posix()
            for line, target in _local_import_targets(path):
                if rel.startswith("experimental/") and not target.startswith(APPROVED_EXPERIMENTAL_IMPORTS):
                    violations.append(f"{rel}:{line} -> {target}")
                if rel.startswith("apps/") and not target.startswith(APPROVED_APP_IMPORTS):
                    violations.append(f"{rel}:{line} -> {target}")

        self.assertEqual(violations, [], msg="App/experimental layer imported an internal-only module:\n" + "\n".join(violations))

    def test_public_entrypoints_use_the_approved_surface(self):
        graph = build_import_graph(ROOT)
        api_main_imports = [
            edge["target"]
            for edge in graph["edges"]
            if edge["source"] == "api/main.py"
        ]
        replay_imports = [
            edge["target"]
            for edge in graph["edges"]
            if edge["source"] == "scripts/replay_execution.py"
        ]

        self.assertIn("core.api", api_main_imports)
        self.assertNotIn("scripts.router", api_main_imports)
        self.assertIn("core.api", replay_imports)
        self.assertNotIn("scripts.router", replay_imports)
        self.assertNotIn("core.execution_audit", replay_imports)


def _local_import_targets(path: Path) -> list[tuple[int, str]]:
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append((getattr(node, "lineno", 0), alias.name))
        elif isinstance(node, ast.ImportFrom) and node.module:
            target = node.module
            if node.level:
                target = "." * node.level + target
            targets.append((getattr(node, "lineno", 0), target))
    return targets


if __name__ == "__main__":
    unittest.main()
