from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from memory.log import record_feedback as record_feedback_impl
from scripts.semantic_router import route_task_semantically
from syncmaster.audio import analyze_audio_file as syncmaster_analyze_audio_file_impl
from syncmaster.graph import query_graph as syncmaster_query_graph_impl
from syncmaster.graph import save_brief as syncmaster_save_brief_impl
from syncmaster.graph import save_recommendation as syncmaster_save_recommendation_impl
from syncmaster.graph import save_track as syncmaster_save_track_impl
from syncmaster.licensing import recommend_sync_fit
from syncmaster.matching import match_to_brief
from syncmaster.metadata import tag_metadata
from tools.registry import ToolRegistry, ToolValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", "venv"}


def create_default_registry(repo_root: str | Path | None = None) -> ToolRegistry:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    registry = ToolRegistry()
    registry.register_function(
        "read_file",
        "Read a text file inside the repository.",
        lambda path, max_bytes=20000: read_file(path, root=root, max_bytes=max_bytes),
        {
            "type": "object",
            "required": ["path"],
            "additionalProperties": False,
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer"},
            },
        },
    )
    registry.register_function(
        "list_files",
        "List files under a repository path.",
        lambda path=".", pattern="*", max_results=200: list_files(
            path=path,
            root=root,
            pattern=pattern,
            max_results=max_results,
        ),
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "path": {"type": "string"},
                "pattern": {"type": "string"},
                "max_results": {"type": "integer"},
            },
        },
    )
    registry.register_function(
        "search_repo",
        "Search text files in the repository.",
        lambda query, path=".", max_results=100: search_repo(
            query=query,
            path=path,
            root=root,
            max_results=max_results,
        ),
        {
            "type": "object",
            "required": ["query"],
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string"},
                "max_results": {"type": "integer"},
            },
        },
    )
    registry.register_function(
        "route_task",
        "Route a task without executing a model.",
        route_task,
        {
            "type": "object",
            "required": ["task"],
            "additionalProperties": False,
            "properties": {"task": {"type": "string"}},
        },
    )
    registry.register_function(
        "record_feedback",
        "Record feedback for a memory event.",
        record_feedback,
        {
            "type": "object",
            "required": ["event_id", "feedback"],
            "additionalProperties": False,
            "properties": {
                "event_id": {"type": "string"},
                "feedback": {"type": "string"},
                "note": {"type": ["string", "null"]},
            },
        },
    )
    registry.register_function(
        "syncmaster_analyze_metadata",
        "Analyze SyncMaster track metadata.",
        syncmaster_analyze_metadata,
        {
            "type": "object",
            "required": ["payload"],
            "additionalProperties": False,
            "properties": {"payload": {"type": "object"}},
        },
    )
    registry.register_function(
        "syncmaster_analyze_audio",
        "Analyze a local SyncMaster audio file and merge audio-derived features into metadata.",
        syncmaster_analyze_audio,
        {
            "type": "object",
            "required": ["audio_path"],
            "additionalProperties": False,
            "properties": {
                "audio_path": {"type": "string"},
                "payload": {"type": "object"},
            },
        },
    )
    registry.register_function(
        "syncmaster_recommend_sync_fit",
        "Recommend sync licensing fit for a track and brief.",
        syncmaster_recommend_sync_fit,
        {
            "type": "object",
            "required": ["track_metadata", "brief"],
            "additionalProperties": False,
            "properties": {
                "track_metadata": {"type": "object"},
                "brief": {"type": "object"},
            },
        },
    )
    registry.register_function(
        "syncmaster_match_brief",
        "Rank tracks or composer profiles against a SyncMaster brief.",
        syncmaster_match_brief,
        {
            "type": "object",
            "required": ["brief", "candidates"],
            "additionalProperties": False,
            "properties": {
                "brief": {"type": "object"},
                "candidates": {"type": "array"},
                "limit": {"type": "integer"},
            },
        },
    )
    registry.register_function(
        "syncmaster_save_track",
        "Persist a SyncMaster track node.",
        syncmaster_save_track,
        {
            "type": "object",
            "required": ["track"],
            "additionalProperties": False,
            "properties": {
                "track": {"type": "object"},
                "track_id": {"type": ["string", "null"]},
            },
        },
    )
    registry.register_function(
        "syncmaster_save_brief",
        "Persist a SyncMaster brief node.",
        syncmaster_save_brief,
        {
            "type": "object",
            "required": ["brief"],
            "additionalProperties": False,
            "properties": {
                "brief": {"type": "object"},
                "brief_id": {"type": ["string", "null"]},
            },
        },
    )
    registry.register_function(
        "syncmaster_save_recommendation",
        "Persist a SyncMaster recommendation node and links.",
        syncmaster_save_recommendation,
        {
            "type": "object",
            "required": ["recommendation"],
            "additionalProperties": False,
            "properties": {
                "recommendation": {"type": "object"},
                "track_id": {"type": ["string", "null"]},
                "brief_id": {"type": ["string", "null"]},
                "recommendation_id": {"type": ["string", "null"]},
            },
        },
    )
    registry.register_function(
        "syncmaster_query_graph",
        "Query SyncMaster graph memory.",
        syncmaster_query_graph,
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "node_id": {"type": ["string", "null"]},
                "relation": {"type": ["string", "null"]},
                "direction": {"type": "string"},
            },
        },
    )
    _register_agent_alias(registry, "local_model")
    _register_agent_alias(registry, "code_agent")
    _register_agent_alias(registry, "audio_agent")
    _register_agent_alias(registry, "sync_agent")
    registry.register_function(
        "memory",
        "Review the current task context without mutating learning state.",
        lambda task=None: review_memory(task=task),
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {"task": {"type": "string"}},
        },
    )
    return registry


def read_file(path: str, root: str | Path | None = None, max_bytes: int = 20000) -> dict[str, Any]:
    file_path = _safe_path(path, root)
    if not file_path.is_file():
        raise ToolValidationError(f"Not a file: {path}")
    if max_bytes <= 0:
        raise ToolValidationError("max_bytes must be greater than zero.")

    data = file_path.read_bytes()
    chunk = data[:max_bytes]
    return {
        "path": _relative(file_path, root),
        "content": chunk.decode("utf-8", errors="replace"),
        "bytes_read": len(chunk),
        "truncated": len(data) > len(chunk),
    }


def list_files(
    path: str = ".",
    root: str | Path | None = None,
    pattern: str = "*",
    max_results: int = 200,
) -> dict[str, Any]:
    base = _safe_path(path, root)
    if not base.exists():
        raise ToolValidationError(f"Path does not exist: {path}")
    if max_results <= 0:
        raise ToolValidationError("max_results must be greater than zero.")

    candidates = base.rglob(pattern) if base.is_dir() else [base]
    files = []
    for candidate in candidates:
        if _is_skipped(candidate):
            continue
        if candidate.is_file():
            files.append(_relative(candidate, root))
        if len(files) >= max_results:
            break

    return {"path": _relative(base, root), "files": sorted(files), "truncated": len(files) >= max_results}


def search_repo(
    query: str,
    path: str = ".",
    root: str | Path | None = None,
    max_results: int = 100,
) -> dict[str, Any]:
    if not query:
        raise ToolValidationError("query must be non-empty.")
    if max_results <= 0:
        raise ToolValidationError("max_results must be greater than zero.")

    base = _safe_path(path, root)
    if not base.exists():
        raise ToolValidationError(f"Path does not exist: {path}")
    files = [base] if base.is_file() else [item for item in base.rglob("*") if item.is_file()]
    matches = []
    lowered_query = query.lower()
    for file_path in files:
        if _is_skipped(file_path):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for index, line in enumerate(lines, start=1):
            if lowered_query in line.lower():
                matches.append(
                    {
                        "path": _relative(file_path, root),
                        "line_number": index,
                        "line": line,
                    }
                )
                if len(matches) >= max_results:
                    return {"query": query, "matches": matches, "truncated": True}

    return {"query": query, "matches": matches, "truncated": False}


def route_task(task: str) -> dict[str, Any]:
    decision = route_task_semantically(task, embedding_provider=lambda texts: None)
    return decision.to_dict()


def review_memory(task: str | None = None) -> dict[str, Any]:
    task_text = (task or "").strip()
    words = [word for word in re.findall(r"[A-Za-z0-9_]+", task_text.lower()) if word]
    return {
        "status": "reviewed",
        "task": task_text,
        "word_count": len(words),
        "keywords": words[:8],
    }


def record_feedback(event_id: str, feedback: str, note: str | None = None) -> dict[str, Any]:
    return record_feedback_impl(event_id, feedback, note)


def syncmaster_analyze_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    return tag_metadata(payload=payload)


def syncmaster_analyze_audio(audio_path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return syncmaster_analyze_audio_file_impl(audio_path, payload=payload or {})


def syncmaster_recommend_sync_fit(track_metadata: dict[str, Any], brief: dict[str, Any]) -> dict[str, Any]:
    return recommend_sync_fit(track_metadata, brief)


def syncmaster_match_brief(brief: dict[str, Any], candidates: list[dict[str, Any]], limit: int | None = None):
    return match_to_brief(brief, candidates, limit=limit)


def syncmaster_save_track(track: dict[str, Any], track_id: str | None = None) -> dict[str, Any]:
    return syncmaster_save_track_impl(track, track_id=track_id)


def syncmaster_save_brief(brief: dict[str, Any], brief_id: str | None = None) -> dict[str, Any]:
    return syncmaster_save_brief_impl(brief, brief_id=brief_id)


def syncmaster_save_recommendation(
    recommendation: dict[str, Any],
    track_id: str | None = None,
    brief_id: str | None = None,
    recommendation_id: str | None = None,
) -> dict[str, Any]:
    return syncmaster_save_recommendation_impl(
        recommendation,
        track_id=track_id,
        brief_id=brief_id,
        recommendation_id=recommendation_id,
    )


def syncmaster_query_graph(node_id: str | None = None, relation: str | None = None, direction: str = "both"):
    return syncmaster_query_graph_impl(node_id=node_id, relation=relation, direction=direction)


def _register_agent_alias(registry: ToolRegistry, name: str) -> None:
    registry.register_function(
        name,
        f"Route a task through the {name} planning alias.",
        lambda task, **kwargs: route_task(task),
        {
            "type": "object",
            "required": ["task"],
            "additionalProperties": True,
            "properties": {"task": {"type": "string"}},
        },
    )


def _safe_path(path: str, root: str | Path | None = None) -> Path:
    root_path = Path(root).resolve() if root else REPO_ROOT
    resolved = (root_path / path).resolve()
    if resolved != root_path and root_path not in resolved.parents:
        raise ToolValidationError(f"Path escapes repository root: {path}")
    return resolved


def _relative(path: Path, root: str | Path | None = None) -> str:
    root_path = Path(root).resolve() if root else REPO_ROOT
    return str(path.resolve().relative_to(root_path))


def _is_skipped(path: Path) -> bool:
    return any(part in SKIPPED_DIRS for part in path.parts)
