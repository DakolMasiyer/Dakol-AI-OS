import json
import os
from copy import deepcopy


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
GRAPH_FILE = os.path.join(BASE_DIR, "memory", "graph_store.json")


def _empty_graph():
    return {"nodes": {}, "edges": []}


def _coerce_properties(properties):
    return dict(properties) if isinstance(properties, dict) else {}


def _normalize_node(node_id, value):
    if not isinstance(value, dict):
        value = {}

    properties = _coerce_properties(value.get("properties"))
    node = {
        "id": str(value.get("id") or node_id),
        "type": value.get("type"),
        "properties": properties,
    }

    for key, item in value.items():
        if key not in node and key != "properties":
            node[key] = item

    return node


def _normalize_edge(value):
    if not isinstance(value, dict):
        return None

    source = value.get("source")
    relation = value.get("relation")
    target = value.get("target")
    if source is None or relation is None or target is None:
        return None

    edge = {
        "source": str(source),
        "relation": str(relation),
        "target": str(target),
        "properties": _coerce_properties(value.get("properties")),
    }

    for key, item in value.items():
        if key not in edge and key != "properties":
            edge[key] = item

    return edge


def _normalize_graph(data):
    graph = _empty_graph()
    if not isinstance(data, dict):
        return graph

    nodes = data.get("nodes", {})
    if isinstance(nodes, dict):
        for node_id, node in nodes.items():
            normalized = _normalize_node(str(node_id), node)
            graph["nodes"][normalized["id"]] = normalized
    elif isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict) and node.get("id") is not None:
                normalized = _normalize_node(str(node["id"]), node)
                graph["nodes"][normalized["id"]] = normalized

    edges = data.get("edges", [])
    if isinstance(edges, list):
        for edge in edges:
            normalized = _normalize_edge(edge)
            if normalized is not None:
                graph["edges"].append(normalized)

    return graph


def load_graph(path=None):
    graph_path = path or GRAPH_FILE
    try:
        with open(graph_path, "r") as graph_file:
            return _normalize_graph(json.load(graph_file))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return _empty_graph()


def save_graph(graph, path=None):
    graph_path = path or GRAPH_FILE
    os.makedirs(os.path.dirname(graph_path), exist_ok=True)
    normalized = _normalize_graph(graph)
    with open(graph_path, "w") as graph_file:
        json.dump(normalized, graph_file, indent=2, sort_keys=True)
    return normalized


def create_node(node_id, node_type=None, properties=None, path=None, **metadata):
    if node_id is None:
        raise ValueError("node_id is required")

    graph = load_graph(path)
    node_key = str(node_id)
    existing = graph["nodes"].get(node_key, {"id": node_key, "type": None, "properties": {}})

    existing["id"] = node_key
    if node_type is not None:
        existing["type"] = node_type
    elif "type" not in existing:
        existing["type"] = None

    current_properties = _coerce_properties(existing.get("properties"))
    current_properties.update(_coerce_properties(properties))
    existing["properties"] = current_properties
    existing.update(metadata)

    graph["nodes"][node_key] = existing
    save_graph(graph, path)
    return deepcopy(existing)


def get_node(node_id, path=None):
    if node_id is None:
        return None
    node = load_graph(path)["nodes"].get(str(node_id))
    return deepcopy(node) if node is not None else None


def list_nodes(node_type=None, path=None):
    nodes = load_graph(path)["nodes"].values()
    if node_type is not None:
        nodes = [node for node in nodes if node.get("type") == node_type]
    return [deepcopy(node) for node in sorted(nodes, key=lambda item: item.get("id", ""))]


def _edge_index(edges, source, relation, target):
    for index, edge in enumerate(edges):
        if edge["source"] == source and edge["relation"] == relation and edge["target"] == target:
            return index
    return None


def add_edge(source, relation, target, properties=None, path=None, **metadata):
    if source is None or relation is None or target is None:
        raise ValueError("source, relation, and target are required")

    graph = load_graph(path)
    source_key = str(source)
    relation_key = str(relation)
    target_key = str(target)

    graph["nodes"].setdefault(source_key, {"id": source_key, "type": None, "properties": {}})
    graph["nodes"].setdefault(target_key, {"id": target_key, "type": None, "properties": {}})

    edge = {
        "source": source_key,
        "relation": relation_key,
        "target": target_key,
        "properties": _coerce_properties(properties),
    }
    edge.update(metadata)

    index = _edge_index(graph["edges"], source_key, relation_key, target_key)
    if index is None:
        graph["edges"].append(edge)
        saved_edge = edge
    else:
        existing = graph["edges"][index]
        merged_properties = _coerce_properties(existing.get("properties"))
        merged_properties.update(edge["properties"])
        existing.update(metadata)
        existing["properties"] = merged_properties
        graph["edges"][index] = existing
        saved_edge = existing

    save_graph(graph, path)
    return deepcopy(saved_edge)


def list_edges(source=None, relation=None, target=None, path=None):
    edges = load_graph(path)["edges"]

    def matches(edge):
        return (
            (source is None or edge.get("source") == str(source))
            and (relation is None or edge.get("relation") == str(relation))
            and (target is None or edge.get("target") == str(target))
        )

    return [deepcopy(edge) for edge in edges if matches(edge)]


def query_relations(node_id, relation=None, direction="out", path=None):
    if node_id is None:
        return []
    if direction not in {"out", "in", "both"}:
        raise ValueError("direction must be one of: out, in, both")

    node_key = str(node_id)
    edges = list_edges(relation=relation, path=path)
    results = []
    for edge in edges:
        is_out = edge.get("source") == node_key
        is_in = edge.get("target") == node_key
        if direction == "out" and is_out:
            results.append(edge)
        elif direction == "in" and is_in:
            results.append(edge)
        elif direction == "both" and (is_out or is_in):
            results.append(edge)
    return results


class MemoryGraph:
    def __init__(self, path=None):
        self.path = path

    def load(self):
        return load_graph(self.path)

    def save(self, graph):
        return save_graph(graph, self.path)

    def create_node(self, node_id, node_type=None, properties=None, **metadata):
        return create_node(node_id, node_type=node_type, properties=properties, path=self.path, **metadata)

    def get_node(self, node_id):
        return get_node(node_id, path=self.path)

    def list_nodes(self, node_type=None):
        return list_nodes(node_type=node_type, path=self.path)

    def add_edge(self, source, relation, target, properties=None, **metadata):
        return add_edge(source, relation, target, properties=properties, path=self.path, **metadata)

    def list_edges(self, source=None, relation=None, target=None):
        return list_edges(source=source, relation=relation, target=target, path=self.path)

    def query_relations(self, node_id, relation=None, direction="out"):
        return query_relations(node_id, relation=relation, direction=direction, path=self.path)
