"""Tests for Resource Manager."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.resource_manager import ResourceManager

@pytest.fixture
def rm():
    with tempfile.TemporaryDirectory() as d:
        yield ResourceManager(data_dir=d, budgets={"cpu": 10, "memory": 10, "max_concurrent": 2})

def test_allocate_release(rm):
    assert rm.allocate("t1", {"cpu": 2, "memory": 3}) is True
    usage = rm.get_usage()
    assert usage["cpu"] == 2
    rm.release("t1")
    assert rm.get_usage()["cpu"] == 0

def test_concurrency_limit(rm):
    rm.allocate("a", {"cpu": 1})
    rm.allocate("b", {"cpu": 1})
    assert rm.allocate("c", {"cpu": 1}) is False

def test_recommendations(rm):
    rm.allocate("x", {"cpu": 9, "memory": 9})
    recs = rm.recommend_adjustments()
    assert len(recs) > 0
