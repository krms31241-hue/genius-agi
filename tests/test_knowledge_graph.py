"""Comprehensive tests for Knowledge Graph Engine."""
import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.world.graph import KnowledgeGraph, GraphNode, GraphEdge
from executive.world.relationship import RelationshipManager, RelationshipType
from executive.world.traversal import TraversalEngine
from executive.world.query import GraphQueryEngine
from executive.world.world_model import WorldModel

@pytest.fixture
def rel_mgr():
    return RelationshipManager()

@pytest.fixture
def graph(rel_mgr):
    return KnowledgeGraph(rel_manager=rel_mgr)

@pytest.fixture
def populated_graph(graph):
    graph.add_node("A", "server")
    graph.add_node("B", "db")
    graph.add_node("C", "cache")
    graph.add_node("D", "app")
    graph.add_edge("A", "B", RelationshipType.DEPENDS_ON, weight=2.0)
    graph.add_edge("B", "C", RelationshipType.CONTAINS, weight=1.0)
    graph.add_edge("A", "D", RelationshipType.CONTROLS, weight=1.5)
    return graph

def test_node_creation(graph):
    n = graph.add_node("n1", "test", {"k": "v"})
    assert n.id == "n1"
    assert n.entity_type == "test"
    assert n.attributes["k"] == "v"
    assert "n1" in graph.nodes

def test_edge_creation(graph):
    graph.add_node("src")
    graph.add_node("tgt")
    e = graph.add_edge("src", "tgt", RelationshipType.USES, weight=0.5)
    assert e is not None
    assert e.rel_type == RelationshipType.USES
    assert e.weight == 0.5
    assert "tgt" in graph.adj["src"]

def test_duplicate_prevention(graph):
    graph.add_node("x")
    graph.add_node("y")
    e1 = graph.add_edge("x", "y", RelationshipType.RELATED_TO)
    e2 = graph.add_edge("x", "y", RelationshipType.RELATED_TO)
    assert e1.id == e2.id
    assert len(graph.edges) == 1

def test_dangling_reference_prevention(graph):
    graph.add_node("valid")
    e = graph.add_edge("valid", "invalid", RelationshipType.USES)
    assert e is None

def test_integrity_validation(graph):
    graph.add_node("a")
    graph.add_node("b")
    graph.add_edge("a", "b", RelationshipType.RELATED_TO)
    assert len(graph.validate_integrity()) == 0
    # Simulate corruption
    del graph.nodes["b"]
    issues = graph.validate_integrity()
    assert len(issues) == 1
    assert "dangling target" in issues[0]

def test_bfs(populated_graph):
    trav = TraversalEngine(populated_graph)
    order = trav.bfs("A")
    assert order[0] == "A"
    assert set(order) == {"A", "B", "C", "D"}

def test_dfs(populated_graph):
    trav = TraversalEngine(populated_graph)
    order = trav.dfs("A")
    assert order[0] == "A"
    assert set(order) == {"A", "B", "C", "D"}

def test_shortest_path(populated_graph):
    trav = TraversalEngine(populated_graph)
    path, cost = trav.shortest_path("A", "C")
    assert path == ["A", "B", "C"]
    assert cost == 3.0

def test_connected_components(populated_graph):
    populated_graph.add_node("E", "isolated")
    trav = TraversalEngine(populated_graph)
    comps = trav.connected_components()
    assert len(comps) == 2
    assert {"A", "B", "C", "D"} in comps
    assert {"E"} in comps

def test_reachability_ancestors_descendants(populated_graph):
    trav = TraversalEngine(populated_graph)
    assert trav.is_reachable("A", "C") is True
    assert trav.is_reachable("C", "A") is False
    assert set(trav.ancestors("C")) == {"A", "B"}
    assert set(trav.descendants("A")) == {"B", "C", "D"}

def test_query_engine(populated_graph):
    qe = GraphQueryEngine(populated_graph)
    assert qe.find_by_id("A").entity_type == "server"
    assert len(qe.find_by_type("db")) == 1
    neighbors = qe.find_neighbors("A")
    assert len(neighbors) == 2
    rels = qe.find_relationship("A", "B")
    assert len(rels) == 1
    assert rels[0]["rel_type"] == RelationshipType.DEPENDS_ON
    isolated = qe.find_isolated_entities()
    assert len(isolated) == 0
    stats = qe.get_statistics()
    assert stats["nodes"] == 4
    assert stats["edges"] == 3

def test_serialization(populated_graph):
    data = populated_graph.to_dict()
    restored = KnowledgeGraph.from_dict(data, populated_graph.rel_manager)
    assert len(restored.nodes) == 4
    assert len(restored.edges) == 3
    assert restored.adj["A"] == populated_graph.adj["A"]

def test_persistence(populated_graph):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "graph.json")
        with open(path, 'w') as f:
            json.dump(populated_graph.to_dict(), f)
        with open(path, 'r') as f:
            data = json.load(f)
        restored = KnowledgeGraph.from_dict(data, populated_graph.rel_manager)
        assert len(restored.nodes) == 4
        assert len(restored.edges) == 3

def test_world_model_integration():
    with tempfile.TemporaryDirectory() as tmpdir:
        wm = WorldModel(data_dir=tmpdir)
        e1 = wm.create_entity("server", {"ip": "1.1.1.1"})
        e2 = wm.create_entity("db", {"port": 5432})
        
        kg = KnowledgeGraph()
        kg.sync_from_world_model(wm)
        assert e1.id in kg.nodes
        assert e2.id in kg.nodes
        assert kg.nodes[e1.id].entity_type == "server"
        
        kg.add_edge(e1.id, e2.id, RelationshipType.DEPENDS_ON)
        assert len(kg.edges) == 1
        assert kg.validate_integrity() == []
