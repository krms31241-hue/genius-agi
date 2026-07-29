"""Comprehensive tests for Executive Intelligence Core."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.executive_engine import ExecutiveEngine
from executive.goal import GoalManager
from executive.goal_generator import GoalGenerator
from executive.goal_priority import GoalPriorityEngine
from executive.goal_decomposer import GoalDecomposer
from executive.planner import Planner
from executive.task_graph import TaskGraph
from executive.scheduler import Scheduler
from executive.progress_tracker import ProgressTracker
from executive.execution_monitor import ExecutionMonitor
from executive.replanner import Replanner
from executive.executive_models import Goal, GoalStatus, PlanNode, TaskState

@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def engine(data_dir):
    return ExecutiveEngine(data_dir=os.path.join(data_dir, "exec"))

@pytest.fixture
def context():
    return {
        "memory_stats": {"recall_rate": 60, "compression_ratio": 0.5},
        "decision_stats": {"avg_confidence": 0.5},
        "governance_stats": {"policy_violations": 2},
        "failure_stats": {"recent_failures": 5},
        "user_requests": [{"id": "u1", "description": "Optimize pipeline", "importance": 0.9, "urgency": 0.8}]
    }

def test_goal_creation(data_dir):
    mgr = GoalManager(data_dir=data_dir)
    g = Goal(title="test", description="desc", importance=0.8, urgency=0.7)
    assert mgr.add_goal(g) is True
    loaded = mgr.get_goal(g.id)
    assert loaded.title == "test"
    assert loaded.status == GoalStatus.NEW

def test_goal_status_transition(data_dir):
    mgr = GoalManager(data_dir=data_dir)
    g = Goal(title="trans", status=GoalStatus.NEW)
    mgr.add_goal(g)
    assert mgr.transition_status(g, GoalStatus.PLANNED) is True
    assert g.status == GoalStatus.PLANNED
    assert mgr.transition_status(g, GoalStatus.RUNNING) is False

def test_goal_generation(context):
    gen = GoalGenerator()
    goals = gen.generate(context)
    assert len(goals) >= 4
    assert all(g.origin in ("memory_telemetry", "decision_engine", "governance_engine", "failure_history", "user", "system") for g in goals)

def test_priority_scoring():
    pri = GoalPriorityEngine()
    goals = [Goal(title="a", importance=0.9, urgency=0.8, metadata={"risk": 0.2, "expected_value": 0.9, "resource_cost": 0.3, "confidence": 0.8}),
             Goal(title="b", importance=0.4, urgency=0.3, metadata={"risk": 0.8, "expected_value": 0.4, "resource_cost": 0.8, "confidence": 0.4})]
    scored = pri.score_goals(goals)
    assert scored[0].title == "a"
    assert scored[0].priority > scored[1].priority

def test_goal_decomposition():
    dec = GoalDecomposer()
    g = Goal(title="main", description="decompose me", metadata={"atomic": False})
    tree = dec.decompose(g, max_depth=2)
    assert len(tree) > 1
    assert any(sub.parent_goal == g.id for sub in tree)
    assert all(sub.metadata.get("atomic") for sub in tree if not sub.child_goals)

def test_planner():
    pln = Planner()
    goals = [Goal(title="t1", description="action1", metadata={"atomic": True, "risk": 0.2}),
             Goal(title="t2", description="action2", dependencies=["t1"], metadata={"atomic": True, "risk": 0.7})]
    nodes = pln.create_plan(goals)
    assert len(nodes) == 2
    assert nodes[1].branch_type == "conditional"

def test_task_graph_dag():
    g = TaskGraph()
    g.add_node(PlanNode(id="a", action="A"))
    g.add_node(PlanNode(id="b", action="B", dependencies=["a"]))
    g.add_node(PlanNode(id="c", action="C", dependencies=["a"]))
    g.add_node(PlanNode(id="d", action="D", dependencies=["b", "c"]))
    assert g.validate_deps() is True
    assert g.detect_cycle() is False
    order = g.topological_sort()
    assert order.index("a") < order.index("b")
    assert order.index("a") < order.index("c")
    path, cost = g.critical_path()
    assert "a" in path and "d" in path

def test_task_graph_cycle():
    g = TaskGraph()
    g.add_node(PlanNode(id="x", action="X", dependencies=["y"]))
    g.add_node(PlanNode(id="y", action="Y", dependencies=["x"]))
    assert g.detect_cycle() is True
    with pytest.raises(ValueError):
        g.topological_sort()

def test_scheduler():
    g = TaskGraph()
    g.add_node(PlanNode(id="1", action="1"))
    g.add_node(PlanNode(id="2", action="2", dependencies=["1"]))
    g.add_node(PlanNode(id="3", action="3", dependencies=["1"]))
    sched = Scheduler(g, {"1": 50, "2": 80, "3": 60})
    order = sched.schedule()
    assert order[0] == "1"
    assert "2" in order and "3" in order

def test_progress_tracker():
    trk = ProgressTracker()
    trk.init_tasks(["t1", "t2", "t3"])
    trk.update("t1", GoalStatus.COMPLETED, 100.0)
    trk.update("t2", GoalStatus.RUNNING, 45.0)
    prog = trk.get_progress()
    assert prog["completed"] == 1
    assert prog["running"] == 1
    assert prog["percentage"] == pytest.approx(33.33, abs=0.1)

def test_execution_monitor():
    g = TaskGraph()
    g.add_node(PlanNode(id="m1", action="M1"))
    g.add_node(PlanNode(id="m2", action="M2", dependencies=["m1"]))
    states = {"m1": TaskState(node_id="m1", status=GoalStatus.COMPLETED, started_at=time.time()-10, completed_at=time.time()-5),
              "m2": TaskState(node_id="m2", status=GoalStatus.RUNNING, started_at=time.time()-2)}
    mon = ExecutionMonitor(g, states, timeout_sec=1.0)
    metrics = mon.analyze()
    assert metrics.deadlock_detected is False
    assert metrics.running == 1

def test_replanner():
    g = TaskGraph()
    g.add_node(PlanNode(id="r1", action="R1"))
    g.add_node(PlanNode(id="r2", action="R2", dependencies=["r1"]))
    states = {"r1": TaskState(node_id="r1", status=GoalStatus.COMPLETED), "r2": TaskState(node_id="r2", status=GoalStatus.FAILED)}
    rep = Replanner()
    new_g = rep.replan(g, states, ["r2"])
    assert "r1" in new_g.nodes
    assert "r2" not in new_g.nodes
    assert any("alt" in nid for nid in new_g.nodes)

def test_persistence(data_dir):
    mgr = GoalManager(data_dir=data_dir)
    g = Goal(title="persist", status=GoalStatus.NEW)
    mgr.add_goal(g)
    mgr.transition_status(g, GoalStatus.PLANNED)
    mgr2 = GoalManager(data_dir=data_dir)
    loaded = mgr2.get_goal(g.id)
    assert loaded.status == GoalStatus.PLANNED

def test_executive_engine_integration(engine, context):
    res = engine.run_pipeline(context)
    assert res["status"] == "success"
    assert res["goals_generated"] >= 4
    assert res["tasks_scheduled"] > 0
    assert res["graph_valid"] is True
    assert res["progress"]["total"] > 0

def test_executive_failure_handling(engine, context):
    engine.run_pipeline(context)
    first_task = list(engine.tracker.states.keys())[0]
    res = engine.handle_failure(first_task)
    assert res["status"] == "replanned"
    assert res["new_tasks"] >= 0
