"""Comprehensive tests for Executive Stage 3: Mission Executor, Context, History, Recovery."""
import os
import sys
import time
import tempfile
import pytest
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.execution_context import ExecutionContext, ContextStatus
from executive.execution_history import ExecutionHistory, TaskExecutionRecord
from executive.recovery_manager import RecoveryManager, FailureType, RecoveryStrategy
from executive.mission_executor import MissionExecutor
from executive.mission import MissionManager, Mission, MissionStatus
from executive.goal import GoalManager
from executive.resource_manager import ResourceManager
from executive.task_graph import TaskGraph
from executive.adaptive_scheduler import AdaptiveScheduler
from executive.executive_models import PlanNode

@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def setup_executor(data_dir):
    mm = MissionManager(data_dir=data_dir)
    gm = GoalManager(data_dir=data_dir)
    rm = ResourceManager(data_dir=data_dir, budgets={"cpu": 100, "memory": 100, "max_concurrent": 10})
    return mm, gm, rm

def test_execution_context_lifecycle():
    ctx = ExecutionContext(mission_id="m1")
    assert ctx.status == ContextStatus.RUNNING
    ctx.push_task("t1")
    assert ctx.current_task_id == "t1"
    assert len(ctx.execution_stack) == 1
    ctx.pop_task()
    assert ctx.current_task_id is None
    ctx.status = ContextStatus.PAUSED
    d = ctx.to_dict()
    assert d["status"] == "paused"
    restored = ExecutionContext.from_dict(d)
    assert restored.status == ContextStatus.PAUSED

def test_execution_history_persistence(data_dir):
    hist = ExecutionHistory(data_dir=data_dir)
    rec = TaskExecutionRecord(task_id="t1", mission_id="m1", started_at=100.0, completed_at=105.0, duration=5.0, status="success")
    hist.record_task(rec)
    loaded = hist.get_history(mission_id="m1")
    assert len(loaded) == 1
    assert loaded[0].task_id == "t1"
    stats = hist.get_task_stats("t1")
    assert stats["successes"] == 1

def test_recovery_classification():
    hist = ExecutionHistory(data_dir=tempfile.mkdtemp())
    rm = RecoveryManager(history=hist, max_retries=2)
    assert rm.classify_failure("Connection timeout reached") == FailureType.TIMEOUT
    assert rm.classify_failure("Memory allocation failed") == FailureType.RESOURCE
    assert rm.classify_failure("Invalid syntax in module") == FailureType.PERMANENT
    assert rm.classify_failure("Temporary network glitch") == FailureType.TRANSIENT
    assert rm.classify_failure("Unknown error") == FailureType.UNKNOWN

def test_recovery_strategy_selection(data_dir):
    hist = ExecutionHistory(data_dir=data_dir)
    rm = RecoveryManager(history=hist, max_retries=1)
    # First failure -> RETRY
    assert rm.get_strategy(FailureType.TRANSIENT, "t1") == RecoveryStrategy.RETRY
    # Record retries to exceed max
    for _ in range(2):
        hist.record_task(TaskExecutionRecord(task_id="t1", mission_id="m1", retry_count=1, status="failed"))
    # Exceeded -> ESCALATE
    assert rm.get_strategy(FailureType.TRANSIENT, "t1") == RecoveryStrategy.ESCALATE
    # Permanent -> ROLLBACK
    assert rm.get_strategy(FailureType.PERMANENT, "t2") == RecoveryStrategy.ROLLBACK

def test_mission_execution_success(setup_executor):
    mm, gm, rm = setup_executor
    g = TaskGraph()
    g.add_node(PlanNode(id="a", action="A", estimated_cost=1.0))
    g.add_node(PlanNode(id="b", action="B", dependencies=["a"], estimated_cost=1.0))
    sched = AdaptiveScheduler(g, rm)
    m = Mission(id="m_exec", title="Exec Test", objectives=["run"])
    mm.create_mission(m)

    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir)
    res = executor.execute_mission(m, g, sched)
    assert res["status"] == "completed"
    assert "a" in res["completed"] and "b" in res["completed"]
    assert m.status == MissionStatus.COMPLETED

def test_mission_execution_failure_and_rollback(setup_executor):
    mm, gm, rm = setup_executor
    g = TaskGraph()
    g.add_node(PlanNode(id="fail_permanent", action="F", estimated_cost=1.0))
    sched = AdaptiveScheduler(g, rm)
    m = Mission(id="m_fail", title="Fail Test", objectives=["break"])
    mm.create_mission(m)

    def runner(tid, ctx):
        raise RuntimeError("Invalid syntax in module")

    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir, task_runner=runner)
    res = executor.execute_mission(m, g, sched)
    assert res["status"] == "rolled_back"
    assert "fail_permanent" in res["failed"]

def test_mission_pause_resume_cancel(setup_executor):
    mm, gm, rm = setup_executor
    g = TaskGraph()
    g.add_node(PlanNode(id="p1", action="P1", estimated_cost=1.0))
    g.add_node(PlanNode(id="p2", action="P2", dependencies=["p1"], estimated_cost=1.0))
    sched = AdaptiveScheduler(g, rm)
    m = Mission(id="m_ctrl", title="Ctrl Test", objectives=["ctrl"])
    mm.create_mission(m)

    pause_triggered = threading.Event()
    resume_triggered = threading.Event()

    def ctrl_runner(tid, ctx):
        if tid == "p1":
            pause_triggered.wait(timeout=2.0)
        return True

    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir, task_runner=ctrl_runner)

    def run_thread():
        return executor.execute_mission(m, g, sched)

    t = threading.Thread(target=run_thread)
    t.start()
    time.sleep(0.1)
    executor.pause()
    assert executor.context.status == ContextStatus.PAUSED
    pause_triggered.set()
    time.sleep(0.1)
    executor.resume()
    assert executor.context.status == ContextStatus.RUNNING
    t.join(timeout=3.0)
    assert not t.is_alive()

def test_mission_cancellation(setup_executor):
    mm, gm, rm = setup_executor
    g = TaskGraph()
    g.add_node(PlanNode(id="c1", action="C1", estimated_cost=1.0))
    g.add_node(PlanNode(id="c2", action="C2", dependencies=["c1"], estimated_cost=1.0))
    sched = AdaptiveScheduler(g, rm)
    m = Mission(id="m_cancel", title="Cancel Test", objectives=["stop"])
    mm.create_mission(m)

    def cancel_runner(tid, ctx):
        if tid == "c1":
            executor.cancel()
        return True

    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir, task_runner=cancel_runner)
    res = executor.execute_mission(m, g, sched)
    assert res["status"] == "cancelled"
    assert executor.context.status == ContextStatus.CANCELLED

def test_checkpoint_persistence_and_restore(setup_executor):
    mm, gm, rm = setup_executor
    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir)
    ctx = ExecutionContext(mission_id="m_ckpt")
    ctx.push_task("t_ckpt")
    executor.context = ctx
    executor._save_checkpoint()
    restored = executor.load_checkpoint()
    assert restored is not None
    assert restored.mission_id == "m_ckpt"
    assert restored.current_task_id == "t_ckpt"

def test_history_recording_on_failure(setup_executor):
    mm, gm, rm = setup_executor
    g = TaskGraph()
    g.add_node(PlanNode(id="h_fail", action="H", estimated_cost=1.0))
    sched = AdaptiveScheduler(g, rm)
    m = Mission(id="m_hist", title="Hist Test", objectives=["record"])
    mm.create_mission(m)

    def fail_runner(tid, ctx):
        raise RuntimeError("transient network glitch")

    executor = MissionExecutor(mm, gm, rm, data_dir=mm.data_dir, task_runner=fail_runner)
    executor.execute_mission(m, g, sched)
    hist = executor.history.get_history(mission_id="m_hist")
    assert len(hist) == 1
    assert hist[0].status == "failed"
    assert "transient" in hist[0].error.lower()
    assert hist[0].retry_count == 1
