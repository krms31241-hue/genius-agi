"""Comprehensive unit tests for the Memory Core."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from memory.memory_manager import MemoryManager
from memory.memory_models import Experience, Fact, Skill

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

def test_working_memory_set_get(manager):
    assert manager.set_working("task_1", {"status": "running"}, ttl=5.0) is True
    val = manager.get_working("task_1")
    assert val == {"status": "running"}

def test_working_memory_expiration(manager):
    manager.set_working("temp", "data", ttl=0.1)
    time.sleep(0.2)
    assert manager.get_working("temp") is None

def test_working_memory_clear(manager):
    manager.set_working("k1", "v1")
    manager.clear_working()
    assert manager.get_working("k1") is None

def test_episodic_memory_add_search(manager):
    exp = Experience(goal="optimize", action="refactor", result="success", success=True, duration=1.2)
    assert manager.add_experience(exp) is True
    res = manager.search_experiences(goal="optimize")
    assert len(res) == 1
    assert res[0].success is True

def test_episodic_memory_stats(manager):
    manager.add_experience(Experience(goal="g1", success=True, duration=1.0))
    manager.add_experience(Experience(goal="g2", success=False, duration=2.0))
    stats = manager.get_episodic_stats()
    assert stats["total_experiences"] == 2
    assert stats["successful"] == 1
    assert stats["failed"] == 1

def test_semantic_memory_crud(manager):
    fact = Fact(title="Python", content="Python is a language.", source="docs", confidence=0.9, tags=["lang", "code"])
    assert manager.add_fact(fact) is True
    res = manager.search_facts("Python")
    assert len(res) == 1
    assert manager.update_fact(fact.id, confidence=0.95) is True
    assert manager.delete_fact(fact.id) is True
    assert len(manager.search_facts("Python")) == 0

def test_skill_memory_learn_list(manager):
    skill = Skill(name="refactor", description="Refactor code", input_schema="{}", output_schema="{}", success_rate=0.8, times_used=5)
    assert manager.learn_skill(skill) is True
    skills = manager.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "refactor"
    assert manager.update_skill("refactor", times_used=6) is True
    assert manager.get_skill("refactor").times_used == 6

def test_index_search(manager):
    manager.add_experience(Experience(goal="security_fix", action="patch", success=True))
    res = manager.search_index("security")
    assert len(res) > 0
    assert res[0]["entity_type"] == "episodic"

def test_persistence(db_path):
    mgr1 = MemoryManager(db_path=db_path)
    mgr1.set_working("persist_key", "persist_val")
    mgr1.add_experience(Experience(goal="test_persist", success=True))
    mgr1.close()

    mgr2 = MemoryManager(db_path=db_path)
    assert mgr2.get_working("persist_key") == "persist_val"
    assert len(mgr2.search_experiences(goal="test_persist")) == 1
    mgr2.close()
