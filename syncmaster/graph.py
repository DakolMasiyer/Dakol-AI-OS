from __future__ import annotations

import re
from typing import Any

from memory.graph import MemoryGraph


def save_track(track: dict[str, Any], track_id: str | None = None, graph: MemoryGraph | None = None) -> dict[str, Any]:
    graph = graph or MemoryGraph()
    track_id = track_id or _track_id(track)
    node_id = f"track:{track_id}"
    node = graph.create_node(node_id, node_type="track", properties=track)

    composer = track.get("composer") or track.get("artist")
    if composer:
        composer_id = f"composer:{_slug(composer)}"
        graph.create_node(composer_id, node_type="composer", properties={"name": composer})
        graph.add_edge(node_id, "COMPOSED_BY", composer_id)

    return node


def save_brief(brief: dict[str, Any], brief_id: str | None = None, graph: MemoryGraph | None = None) -> dict[str, Any]:
    graph = graph or MemoryGraph()
    brief_id = brief_id or _slug(brief.get("title") or brief.get("description") or "brief")
    return graph.create_node(f"brief:{brief_id}", node_type="brief", properties=brief)


def save_recommendation(
    recommendation: dict[str, Any],
    track_id: str | None = None,
    brief_id: str | None = None,
    recommendation_id: str | None = None,
    graph: MemoryGraph | None = None,
) -> dict[str, Any]:
    graph = graph or MemoryGraph()
    recommendation_id = recommendation_id or _slug(
        f"{track_id or 'track'}-{brief_id or 'brief'}-{recommendation.get('fit_score', 'fit')}"
    )
    node_id = f"sync_recommendation:{recommendation_id}"
    node = graph.create_node(node_id, node_type="sync_recommendation", properties=recommendation)

    if track_id:
        graph.add_edge(node_id, "EVALUATES_TRACK", f"track:{track_id}")
    if brief_id:
        graph.add_edge(node_id, "AGAINST_BRIEF", f"brief:{brief_id}")
    return node


def query_graph(node_id: str | None = None, relation: str | None = None, direction: str = "both") -> dict[str, Any]:
    graph = MemoryGraph()
    if node_id:
        return {
            "node": graph.get_node(node_id),
            "relations": graph.query_relations(node_id, relation=relation, direction=direction),
        }
    return {"nodes": graph.list_nodes(), "edges": graph.list_edges(relation=relation)}


def _track_id(track: dict[str, Any]) -> str:
    return _slug(track.get("id") or track.get("title") or track.get("name") or "track")


def _slug(value) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return slug[:80] or "item"
