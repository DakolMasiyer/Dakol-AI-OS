import json
import tempfile
import unittest
from pathlib import Path

from memory.graph import MemoryGraph, load_graph


class MemoryGraphTests(unittest.TestCase):
    def test_missing_store_loads_empty_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"

            self.assertEqual(load_graph(str(graph_path)), {"nodes": {}, "edges": []})

    def test_malformed_store_loads_empty_graph(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph_path.write_text("{not-json")

            self.assertEqual(load_graph(str(graph_path)), {"nodes": {}, "edges": []})

    def test_create_get_and_list_nodes_persist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph = MemoryGraph(str(graph_path))

            graph.create_node("track:1", node_type="track", properties={"title": "Blue"})
            graph.create_node("artist:1", node_type="artist", properties={"name": "Ada"})

            reloaded = MemoryGraph(str(graph_path))

            self.assertEqual(reloaded.get_node("track:1")["properties"]["title"], "Blue")
            self.assertEqual([node["id"] for node in reloaded.list_nodes()], ["artist:1", "track:1"])
            self.assertEqual([node["id"] for node in reloaded.list_nodes("track")], ["track:1"])

    def test_create_node_upserts_existing_node(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph = MemoryGraph(str(graph_path))

            graph.create_node("track:1", node_type="draft", properties={"title": "Old", "bpm": 90})
            updated = graph.create_node("track:1", node_type="track", properties={"title": "New"})

            self.assertEqual(updated["type"], "track")
            self.assertEqual(updated["properties"], {"title": "New", "bpm": 90})
            self.assertEqual(len(graph.list_nodes()), 1)

    def test_add_and_list_edges_persist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph = MemoryGraph(str(graph_path))

            graph.create_node("track:1", node_type="track")
            graph.create_node("artist:1", node_type="artist")
            graph.add_edge("track:1", "performed_by", "artist:1", properties={"confidence": 0.9})

            edge = MemoryGraph(str(graph_path)).list_edges(relation="performed_by")[0]

            self.assertEqual(edge["source"], "track:1")
            self.assertEqual(edge["target"], "artist:1")
            self.assertEqual(edge["properties"]["confidence"], 0.9)

    def test_add_edge_upserts_existing_relation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph = MemoryGraph(str(graph_path))

            graph.add_edge("track:1", "similar_to", "track:2", properties={"score": 0.5})
            updated = graph.add_edge("track:1", "similar_to", "track:2", properties={"reason": "tempo"})

            self.assertEqual(updated["properties"], {"score": 0.5, "reason": "tempo"})
            self.assertEqual(len(graph.list_edges()), 1)

    def test_relation_queries_support_direction_and_relation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph = MemoryGraph(str(graph_path))

            graph.add_edge("track:1", "performed_by", "artist:1")
            graph.add_edge("track:2", "performed_by", "artist:1")
            graph.add_edge("track:1", "similar_to", "track:2")

            outbound = graph.query_relations("track:1", direction="out")
            inbound = graph.query_relations("artist:1", relation="performed_by", direction="in")
            both = graph.query_relations("track:2", direction="both")

            self.assertEqual({edge["relation"] for edge in outbound}, {"performed_by", "similar_to"})
            self.assertEqual({edge["source"] for edge in inbound}, {"track:1", "track:2"})
            self.assertEqual(len(both), 2)

    def test_normalizes_legacy_list_node_store_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            graph_path = Path(temp_dir) / "graph_store.json"
            graph_path.write_text(json.dumps({"nodes": [{"id": "node:1", "type": "concept"}], "edges": []}))

            graph = MemoryGraph(str(graph_path))

            self.assertEqual(graph.get_node("node:1")["type"], "concept")


if __name__ == "__main__":
    unittest.main()
