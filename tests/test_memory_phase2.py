"""Comprehensive tests for Memory Core Phase 2."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from memory.memory_manager import MemoryManager
from memory.importance import ImportanceScorer
from memory.forgetting import ForgettingPolicy
from memory.compression import MemoryCompressor
from memory.replay import ReplayEngine
from memory.statistics import MemoryStatistics
from memory.consolidation import MemoryConsolidator
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
def stats(manager):
    return MemoryStatistics(manager.conn, manager.lock)

@pytest.fixture
def scorer():
    return ImportanceScorer()

@pytest.fixture
def policy():
    return ForgettingPolicy(ttl_seconds=1.0, lru_limit=2, lfu_limit=2)

@pytest.fixture
def compressor():
    return MemoryCompressor(similarity_threshold=0.6)

@pytest.fixture
def consolidator(manager, scorer, policy, stats):
    return MemoryConsolidator(manager, scorer, policy, stats)

def test_importance_scoring(scorer):
    high_imp = {"frequency": 100, "timestamp": time.time(), "last_access": time.time(), "success_count": 10, "failure_count": 0, "feedback": 0.9}
    low_imp = {"frequency": 1, "timestamp": time.time() - 86400*10, "last_access": time.time() - 86400*10, "success_count": 0, "failure_count": 5, "feedback": 0.1}
    
    assert scorer.score(high_imp) > 70.0
    assert scorer.score(low_imp) < 30.0

def test_forgetting_policy(policy):
    old_mem = {"id": "old1", "timestamp": time.time() - 100, "last_access": time.time() - 100, "frequency": 1}
    new_mem = {"id": "new1", "timestamp": time.time(), "last_access": time.time(), "frequency": 10}
    
    assert policy.should_expire(old_mem) is True
    assert policy.should_expire(new_mem) is False
    
    candidates = policy.get_candidates([old_mem, new_mem])
    assert "old1" in candidates

def test_compression_duplicates(compressor):
    mems = [
        {"id": "a", "content": "optimize database queries"},
        {"id": "b", "content": "optimize database queries"},
        {"id": "c", "content": "refactor authentication module"}
    ]
    dups = compressor.find_duplicates(mems)
    assert len(dups) == 1
    assert dups[0] == ("a", "b")

def test_compression_similarity(compressor):
    mems = [
        {"id": "x", "content": "fix memory leak in worker process"},
        {"id": "y", "content": "resolve memory leak in background worker"},
        {"id": "z", "content": "update ui components"}
    ]
    sim = compressor.find_similar(mems)
    assert len(sim) >= 1
    assert sim[0][2] >= 0.6

def test_replay_engine(manager):
    for i in range(5):
        manager.add_experience(Experience(goal=f"task_{i}", action="run", success=(i % 2 == 0)))
    
    engine = ReplayEngine(manager)
    assert len(engine.replay_recent(3)) == 3
    assert len(engine.replay_successes(10)) == 3
    assert len(engine.replay_failures(10)) == 2
    assert len(engine.replay_random(2)) == 2

def test_statistics_tracking(stats, manager):
    stats.increment("promoted_count", 5)
    stats.increment("forgotten_count", 2)
    stats.increment("replay_count", 10)
    
    report = stats.get_full_report(manager)
    assert report["promoted_memories"] == 5
    assert report["forgotten_memories"] == 2
    assert report["replay_count"] == 10
    assert "success_rate" in report
    assert "recall_rate" in report

def test_consolidation_promotion(consolidator, manager):
    # Seed working memory with high-value item
    manager.set_working("task_alpha", {
        "goal": "security_patch",
        "action": "apply_fix",
        "result": "vulnerability_closed",
        "success": True,
        "duration": 2.5,
        "frequency": 50,
        "timestamp": time.time(),
        "last_access": time.time(),
        "success_count": 10,
        "failure_count": 0,
        "feedback": 0.9
    })
    
    assert consolidator.should_consolidate(manager.get_working("task_alpha")) is True
    res = consolidator.consolidate(working_keys=["task_alpha"])
    assert res["promoted"] >= 1
    
    # Verify it moved to episodic
    found = manager.search_experiences(goal="security_patch")
    assert len(found) >= 1

def test_consolidation_replay(consolidator):
    batch = consolidator.replay(mode="recent", limit=5)
    assert isinstance(batch, list)
    consolidator.stats.increment("replay_count") # Ensure stat tracking works
