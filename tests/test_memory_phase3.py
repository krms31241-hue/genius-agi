"""Comprehensive tests for Memory Core Phase 3."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from memory.memory_manager import MemoryManager
from memory.vectorizer import MemoryVectorizer
from memory.semantic_search import SemanticSearch
from memory.link_graph import MemoryGraph
from memory.ranking import MemoryRanker
from memory.hybrid_search import HybridSearch
from memory.context_recall import ContextRecallEngine
from memory.memory_models import Experience, Fact

@pytest.fixture
def db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def manager(db_path):
    mgr = MemoryManager(db_path=db_path)
    yield mgr
    mgr.close()

@pytest.fixture
def vectorizer():
    return MemoryVectorizer(dimension=64)

@pytest.fixture
def sample_memories():
    return [
        {"id": "m1", "goal": "optimize database", "content": "refactor sql queries for speed", "timestamp": time.time()},
        {"id": "m2", "goal": "fix ui bug", "content": "button alignment issue on mobile", "timestamp": time.time() - 100},
        {"id": "m3", "goal": "security patch", "content": "patch sql injection vulnerability", "timestamp": time.time() - 200},
        {"id": "m4", "goal": "update docs", "content": "add api reference documentation", "timestamp": time.time() - 300}
    ]

def test_vectorizer_determinism(vectorizer):
    v1 = vectorizer.vectorize("test deterministic output")
    v2 = vectorizer.vectorize("test deterministic output")
    assert v1 == v2
    assert len(v1) == 64

def test_vectorizer_similarity(vectorizer):
    v1 = vectorizer.vectorize("database optimization techniques")
    v2 = vectorizer.vectorize("optimize database performance")
    v3 = vectorizer.vectorize("ui button styling")
    sim_high = vectorizer.similarity(v1, v2)
    sim_low = vectorizer.similarity(v1, v3)
    assert sim_high > sim_low
    assert sim_high > 0.3

def test_semantic_search(vectorizer, sample_memories):
    engine = SemanticSearch(vectorizer)
    res = engine.search("sql performance", sample_memories, top_k=2)
    assert len(res) == 2
    assert res[0][0]["id"] in ["m1", "m3"]

def test_hybrid_search(vectorizer, sample_memories):
    ranker = MemoryRanker()
    hybrid = HybridSearch(vectorizer, ranker)
    res = hybrid.search("security vulnerability", sample_memories, top_k=2)
    assert len(res) == 2
    assert res[0]["id"] == "m3"

def test_memory_graph(manager):
    assert manager.add_memory_link("exp1", "exp2", "causes") is True
    assert manager.add_memory_link("exp2", "exp3", "related") is True
    related = manager.get_related_memories("exp2")
    assert len(related) == 2
    ids = {r["id"] for r in related}
    assert "exp1" in ids and "exp3" in ids

def test_graph_connected_component(manager):
    manager.add_memory_link("a", "b")
    manager.add_memory_link("b", "c")
    manager.add_memory_link("c", "d")
    component = manager.graph.connected_component("a")
    assert "b" in component and "c" in component and "d" in component

def test_context_recall(manager, sample_memories):
    ctx = manager.get_memory_context("database speed", sample_memories, limit=2)
    assert len(ctx) <= 2
    assert ctx[0]["id"] == "m1"

def test_ranking_order():
    ranker = MemoryRanker()
    mems = [
        {"id": "old", "timestamp": time.time() - 100000, "confidence": 0.9, "success": True},
        {"id": "new", "timestamp": time.time(), "confidence": 0.9, "success": True}
    ]
    ranked = ranker.rank(mems)
    assert ranked[0]["id"] == "new"

def test_manager_integration(manager):
    # Test full pipeline via manager
    exp = Experience(goal="test integration", action="run", result="success", success=True)
    manager.add_experience(exp)
    
    mems = [exp.to_dict()]
    res = manager.search_hybrid("integration test", mems, top_k=1)
    assert len(res) == 1
    assert res[0]["goal"] == "test integration"
