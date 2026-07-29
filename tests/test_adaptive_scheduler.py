"""Tests for Adaptive Scheduler."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.adaptive_scheduler import AdaptiveScheduler
from executive.task_graph import TaskGraph
from executive.resource_manager import ResourceManager
from executive.executive_models import PlanNode

@pytest.fixture
def setup():
    with tempfile.TemporaryDirectory() as d:
        g = TaskGraph()
        g.add_node(PlanNode(id="1", action="A", estimated_cost=1.0))
        g.add_node(PlanNode(id="2", action="B", dependencies=["1"], estimated_cost=1.0))
        rm = ResourceManager(data_dir=d, budgets={"cpu": 100, "memory": 100, "max_concurrent": 5})
        yield g, rm

def test_schedule(setup):
    g, rm = setup
    sched = AdaptiveScheduler(g, rm, {"1": 50, "2": 60})
    res = sched.schedule()
    assert "1" in res and "2" in res

def test_failure_handling(setup):
    g, rm = setup
    sched = AdaptiveScheduler(g, rm)
    sched.schedule()
    sched.handle_failure("1")
    assert "1" in sched.failed
    assert "1" not in sched.scheduled
