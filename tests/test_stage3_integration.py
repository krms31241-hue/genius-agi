"""Executive Stage 3 Final Integration Tests.
Covers end-to-end workflows combining planning, policy, execution, agents, optimization, and reflection."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from governance.governance_manager import GovernanceManager
from governance.policy import Policy

from executive.mission import MissionManager, Mission, MissionStatus
from executive.goal import GoalManager
from executive.resource_manager import ResourceManager
from executive.task_graph import TaskGraph
from executive.adaptive_scheduler import AdaptiveScheduler
from executive.long_horizon_planner import LongHorizonPlanner
from executive.execution_policy import ExecutionPolicyEnforcer
from executive.dynamic_goal_manager import DynamicGoalManager
from executive.goal_priority import GoalPriorityEngine
from executive.agent_coordinator import AgentCoordinator, AgentTask
from executive.runtime_optimizer import RuntimeOptimizer
from executive.autonomous_loop import AutonomousLoop, LoopController
from executive.loop_state import LoopPhase
from executive.self_reflection import SelfReflectionEngine

@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def governance(data_dir):
    return GovernanceManager(data_dir=os.path.join(data_dir, "gov"))

@pytest.fixture
def mission_mgr(data_dir):
    return MissionManager(data_dir=data_dir)

@pytest.fixture
def goal_mgr(data_dir):
    return GoalManager(data_dir=data_dir)

@pytest.fixture
def resource_mgr(data_dir):
    return ResourceManager(data_dir=data_dir, budgets={"cpu": 100, "memory": 100, "max_concurrent": 5})

@pytest.fixture
def planner():
    return LongHorizonPlanner()

@pytest.fixture
def policy_enforcer(governance):
    return ExecutionPolicyEnforcer(governance)

def test_full_mission_lifecycle(mission_mgr, goal_mgr, resource_mgr, planner, policy_enforcer, governance):
    """Plan -> Policy Check -> Execute -> Reflect"""
    # 1. Policy Setup
    pol = Policy(name="safe_exec", version="1.0.0", rules=[
        {"type": "threshold", "target": "risk", "value": 0.8}
    ])
    policy_enforcer.register_and_enable_policy(pol)

    # 2. Mission Decomposition
    res = planner.decompose_mission("m_int_1", "Integration Alpha", ["deploy", "verify"])
    assert res["tree_nodes"] > 5

    # 3. Policy Validation
    exec_ctx = {"risk": 0.4, "mode": "production"}
    policy_res = policy_enforcer.validate_execution(exec_ctx)
    assert policy_res["allowed"] is True

    # 4. Graph & Schedule
    graph = TaskGraph()
    # Simulate adding planned tasks to graph
    for nid in planner.get_execution_plan()[:3]:
        from executive.executive_models import PlanNode
        graph.add_node(PlanNode(id=nid, action=nid, estimated_cost=1.0))
    
    sched = AdaptiveScheduler(graph, resource_mgr)
    scheduled = sched.schedule()
    assert len(scheduled) > 0

    # 5. Reflection
    reflect = SelfReflectionEngine()
    exec_data = {"completed": scheduled, "failed": [], "total_duration": 2.0, "errors": {}}
    report = reflect.reflect("m_int_1_exec", exec_data)
    assert report.success_rate == 1.0
    assert len(report.lessons) > 0

def test_dynamic_injection_and_rescheduling(goal_mgr, resource_mgr):
    """Inject goal during execution and verify scheduler updates"""
    graph = TaskGraph()
    from executive.executive_models import PlanNode
    graph.add_node(PlanNode(id="base", action="Base", estimated_cost=1.0))
    
    sched = AdaptiveScheduler(graph, resource_mgr)
    pri = GoalPriorityEngine()
    dyn_mgr = DynamicGoalManager(goal_mgr, pri, graph, sched)
    
    from executive.executive_models import Goal
    new_goal = Goal(id="dyn_inj", title="Injected", metadata={"atomic": True})
    res = dyn_mgr.inject_goal(new_goal)
    
    assert res["success"] is True
    assert len(res["tasks_added"]) == 1
    assert res["tasks_added"][0] in graph.nodes

def test_agent_coordinator_parallel_execution():
    """Parallel task execution with failure isolation"""
    coord = AgentCoordinator(heartbeat_timeout=5.0, default_timeout=2.0, max_workers=4)
    coord.register_agent("ag1", "Worker1", ["compute"], max_concurrent=2)
    coord.register_agent("ag2", "Worker2", ["io"], max_concurrent=2)
    
    tasks = [
        AgentTask(id="t1", capability="compute", payload={"data": "A"}),
        AgentTask(id="t2", capability="io", payload={"data": "B"}),
        AgentTask(id="t3", capability="compute", payload={"simulate_failure": True})
    ]
    res = coord.execute_parallel(tasks)
    assert "t1" in res["completed"]
    assert "t2" in res["completed"]
    assert "t3" in res["failed"]
    coord.shutdown()

def test_runtime_optimizer_feedback_loop(resource_mgr):
    """Optimizer detects pressure and throttles concurrency"""
    opt = RuntimeOptimizer(cpu_threshold=0.7, memory_threshold=0.7)
    opt.update_metrics({"cpu_usage": 0.9, "memory_usage": 0.4, "queue_depth": 5})
    recs = opt.analyze()
    assert any(r.action_type == "throttle" for r in recs)
    
    result = opt.apply_optimizations(resource_mgr=resource_mgr)
    assert "Reduced concurrency" in result["applied"][0]
    assert resource_mgr.budgets["max_concurrent"] < 5

def test_autonomous_loop_with_reflection():
    """O-A-P-E-E-I loop with integrated reflection phase"""
    ctrl = LoopController(max_iterations=2, max_duration_sec=10.0)
    reflect = SelfReflectionEngine()
    exec_log = {"completed": [], "failed": [], "errors": {}}
    
    def observe_fn(state, ctx):
        ctx["tasks_found"] = 3
        return {"observed": True}
    def analyze_fn(state, ctx): return {"analyzed": True}
    def plan_fn(state, ctx): return {"planned": True}
    def execute_fn(state, ctx):
        exec_log["completed"].append(f"task_{state.iteration}")
        return {"executed": True}
    def evaluate_fn(state, ctx): return {"evaluated": True}
    def improve_fn(state, ctx):
        report = reflect.reflect(f"loop_{state.iteration}", {
            "completed": exec_log["completed"], "failed": [], "total_duration": 0.5, "errors": {}
        })
        ctx["lessons"] = report.lessons
        return {"improved": True}

    loop = AutonomousLoop(ctrl,
        observe_fn=observe_fn, analyze_fn=analyze_fn, plan_fn=plan_fn,
        execute_fn=execute_fn, evaluate_fn=evaluate_fn, improve_fn=improve_fn)
    
    state = loop.run()
    assert state.status.value == "completed"
    assert state.iteration == 2
    assert state.total_successes == 2
    assert len(state.context.get("lessons", [])) > 0

def test_policy_violation_blocks_execution(policy_enforcer, governance):
    """High risk execution must be denied by policy enforcer"""
    pol = Policy(name="strict_risk", version="1.0.0", rules=[
        {"type": "threshold", "target": "risk", "value": 0.3}
    ])
    policy_enforcer.register_and_enable_policy(pol)
    
    ctx = {"risk": 0.8}
    res = policy_enforcer.validate_execution(ctx)
    assert res["allowed"] is False
    assert len(res["violations"]) == 1
    assert "threshold" in res["violations"][0]["reason"]
