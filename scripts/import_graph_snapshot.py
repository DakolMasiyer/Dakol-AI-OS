from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCAN_DIRS = {
    "apps",
    "agents",
    "app",
    "api",
    "core",
    "experimental",
    "farm",
    "memory",
    "planning",
    "platform",
    "runtime",
    "scripts",
    "skills",
    "syncmaster",
    "tools",
    "workflows",
}
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "venv", ".venv", "tests", "logs", "artifacts"}
ALLOWED_LEARNING_IMPORTERS = {
    "agents/orchestrator.py",
    "core/invariants.py",
    "memory/learning.py",
    "scripts/semantic_router.py",
}
DEFAULT_OUTPUT = ROOT / "artifacts" / "import_graph_snapshot.json"


@dataclass(frozen=True)
class ImportEdge:
    source: str
    target: str
    line: int

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "line": self.line}


def build_import_graph(repo_root: Path | None = None) -> dict[str, Any]:
    root = Path(repo_root) if repo_root else ROOT
    modules: list[str] = []
    edges: list[ImportEdge] = []

    for path in sorted(root.rglob("*.py")):
        if _should_skip(path, root):
            continue
        rel_path = path.relative_to(root).as_posix()
        modules.append(rel_path)
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(ImportEdge(rel_path, alias.name, getattr(node, "lineno", 0)))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    target = node.module
                    if node.level:
                        target = "." * node.level + target
                    edges.append(ImportEdge(rel_path, target, getattr(node, "lineno", 0)))

    forbidden_learning_edges = [
        edge.to_dict()
        for edge in edges
        if edge.target.startswith("memory.learning") and edge.source not in ALLOWED_LEARNING_IMPORTERS
    ]

    snapshot = {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "root": str(root),
        "module_count": len(modules),
        "edge_count": len(edges),
        "modules": sorted(modules),
        "edges": [edge.to_dict() for edge in sorted(edges, key=lambda item: (item.source, item.target, item.line))],
        "forbidden_learning_imports": forbidden_learning_edges,
    }
    snapshot["fingerprint"] = _fingerprint({key: value for key, value in snapshot.items() if key != "generated_at"})
    return snapshot


def validate_snapshot(snapshot: dict[str, Any], current: dict[str, Any]) -> list[str]:
    issues = []
    if snapshot.get("fingerprint") != current.get("fingerprint"):
        issues.append("import graph fingerprint mismatch")

    if snapshot.get("forbidden_learning_imports") != current.get("forbidden_learning_imports"):
        issues.append("forbidden learning import set changed")

    return issues


def load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_snapshot(snapshot: dict[str, Any], path: Path = DEFAULT_OUTPUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate a repository import graph snapshot.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Snapshot file to write or validate against")
    parser.add_argument("--validate", action="store_true", help="Validate against an existing snapshot instead of writing")
    args = parser.parse_args(argv)

    output_path = Path(args.output)
    current = build_import_graph(ROOT)

    if args.validate and output_path.exists():
        snapshot = load_snapshot(output_path)
        issues = validate_snapshot(snapshot, current)
        result = {
            "status": "VERIFIED" if not issues else "DEGRADED",
            "issues": issues,
            "snapshot_fingerprint": snapshot.get("fingerprint"),
            "current_fingerprint": current.get("fingerprint"),
        }
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 0 if not issues else 1

    write_snapshot(current, output_path)
    sys.stdout.write(json.dumps({"status": "WRITTEN", "path": str(output_path)}, indent=2) + "\n")
    return 0


def _fingerprint(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(canonical).hexdigest()


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _should_skip(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    parts = set(relative.parts)
    if parts & SKIP_DIRS:
        return True
    if relative.parts and relative.parts[0] not in SCAN_DIRS:
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
