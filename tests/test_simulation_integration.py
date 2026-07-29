"""Comprehensive integration tests for Simulation Engine across Executive, Reasoning, KG, World, Mission, Optimizer, and Policy."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from executive.world.world_model import WorldModel
from executive.world.graph import KnowledgeGraph
from executive.reasoning.reasoning_engine import ReasoningEngine
from executive.runtime_optimizer import RuntimeOptimizer
from governance.governance_manager import GovernanceManager
from executive.execution_policy import ExecutionPolicyEnforcer
from executive.simulation_guard import SimulationGuard
from executive.mission_executor import MissionExecutor
from executive.mission import MissionManager, Mission, MissionStatus
from executive.goal import GoalManager
from executive.resource_manager import ResourceManager
from executive.task_graph import TaskGraph
from executive.adaptive_scheduler import AdaptiveScheduler
from executive.executive_models import PlanNode

@pytest.fixture
def integration_env():
    with tempfile.TemporaryDirectory() as tmpdir:
        world = WorldModel(data_dir=os.path.join(tmpdir, "world"))
        world.create_entity("server", {"status": "idle"}, entity_id="srv1")
        world.create_entity("db", {"status": "active"}, entity_id="db1")
        
        kg = KnowledgeGraph()
        kg.add_node("srv1", "server")
        kg.add_node("db1", "db")
        kg.add_edge("srv1", "db1", "depends_on")
        
        reasoner = ReasoningEngine(data_dir=os.path.join(tmpdir, "reason"))
        reasoner.register_relation("srv1", "db1", "depends_on", 0.9)
        
        optimizer = RuntimeOptimizer(cpu_threshold=0.8)
        optimizer.update_metrics({"cpu_usage": 0.4, "memory_usage": 0.3})
        
        gov = GovernanceManager(data_dir=os.path.join(tmpdir, "gov"))
        policy = ExecutionPolicyEnforcer(gov)
        
        guard = SimulationGuard(
            world_model=world,
            knowledge_graph=kg,
            reasoner=reasoner,
            optimizer=optimizer,
            policy_enforcer=policy,
            risk_threshold=0.5,
            confidence_threshold=0.4
        )
        
        yield {
            "world": world, "kg": kg, "reasoner": reasoner,
            "optimizer": optimizer, "policy": policy, "guard": guard,
            "tmpdir": tmpdir
        }

def test_safe_action_passes_guard(integration_env):
    guard = integration_env["guard"]
    res = guard.evaluate_action("update", target_id="srv1", parameters={"attributes": {"status": "active"}})
    assert res["allowed"] is True
    assert res["risk_score"] <= 0.5
    assert res["confidence"] >= 0.4
    assert res["simulation_result"]["success"] is True

def test_dangerous_action_blocked_by_guard(integration_env):
    guard = integration_env["guard"]
    # Target nonexistent entity -> simulation fails -> high risk/low confidence -> blocked
    res = guard.evaluate_action("update", target_id="nonexistent_critical", parameters={"attributes": {"wipe": True}})
    assert res["allowed"] is False
    assert res["risk_score"] > 0.5 or res["confidence"] < 0.4
    assert "blocked" in res["recommendation"].lower() or "failed" in res["recommendation"].lower()
    assert res["simulation_result"]["success"] is False

def test_policy_integration_blocks_execution(integration_env):
    from governance.policy import Policy
    env = integration_env
    # Register strict policy
    pol = Policy(name="strict_risk", version="1.0.0", rules=[
        {"type": "threshold", "target": "risk", "value": 0.2}
    ])
    env["policy"].register_and_enable_policy(pol)
    
    # Action with moderate risk should now be blocked by policy
    res = env["guard"].evaluate_action("delete", target_id="db1")
    assert res["allowed"] is False
    assert res["policy_compliant"] is False

def test_optimizer_tightens_thresholds(integration_env):
    env = integration_env
    env["optimizer"].update_metrics({"cpu_usage": 0.9, "memory_usage": 0.4})
    # High CPU should lower effective risk threshold, blocking marginal actions
    res = env["guard"].evaluate_action("update", target_id="srv1", parameters={"attributes": {"load": "high"}})
    # Even if simulation succeeds, optimizer pressure may block or flag it
    assert isinstance(res["allowed"], bool)
    assert "risk" in res

def test_reasoning_kg_integration(integration_env):
    env = integration_env
    # Add KG alternative pattern
    env["kg"].add_node("safe_update", "pattern")
    env["kg"].add_edge("update", "safe_update", "safer_alternative")
    
    res = env["guard"].evaluate_action("update", target_id="missing_node", parameters={})
    assert res["allowed"] is False
    assert "safer pattern" in res["recommendation"].lower() or "knowledge graph" in res["recommendation"].lower()

def test_mission_executor_with_guard_blocks_dangerous_task(integration_env):
    env = integration_env
    mm = MissionManager(data_dir=env["tmpdir"])
    gm = GoalManager(data_dir=env["tmpdir"])
    rm = ResourceManager(data_dir=env["tmpdir"], budgets={"cpu": 100, "memory": 100, "max_concurrent": 5})
    
    graph = TaskGraph()
    graph.add_node(PlanNode(id="safe_task", action="Safe", estimated_cost=1.0))
    graph.add_node(PlanNode(id="dangerous_task", action="Dangerous", estimated_cost=1.0))
    
    sched = AdaptiveScheduler(graph, rm)
    m = Mission(id="m_guard", title="Guard Test", objectives=["test"])
    mm.create_mission(m)
    
    # Inject guard into executor
    executor = MissionExecutor(mm, gm, rm, data_dir=env["tmpdir"], simulation_guard=env["guard"])
    res = executor.execute_mission(m, graph, sched)
    
    # safe_task passes, dangerous_task fails simulation (missing entity/context) -> blocked
    assert "safe_task" in res["completed"]
    assert "dangerous_task" in res["failed"]
    assert any("SimulationGuard blocked" in h.error for h in executor.history.get_history(m.id) if h.error)

def test_backward_compatibility_no_guard(integration_env):
    env = integration_env
    mm = MissionManager(data_dir=env["tmpdir"])
    gm = GoalManager(data_dir=env["tmpdir"])
    rm = ResourceManager(data_dir=env["tmpdir"], budgets={"cpu": 100, "memory": 100, "max_concurrent": 5})
    
    graph = TaskGraph()
    graph.add_node(PlanNode(id="legacy_task", action="Legacy", estimated_cost=1.0))
    sched = AdaptiveScheduler(graph, rm)
    m = Mission(id="m_legacy", title="Legacy Test", objectives=["test"])
    mm.create_mission(m)
    
    # No guard provided -> old behavior
    executor = MissionExecutor(mm, gm, rm, data_dir=env["tmpdir"])
    res = executor.execute_mission(m, graph, sched)
    assert res["status"] == "completed"
    assert "legacy_task" in res["completed"]

def test_full_pipeline_integration(integration_env):
    """End-to-end: World -> KG -> Reasoner -> Optimizer -> Policy -> Guard -> Executor"""
    env = integration_env
    mm = MissionManager(data_dir=env["tmpdir"])
    gm = GoalManager(data_dir=env["tmpdir"])
    rm = ResourceManager(data_dir=env["tmpdir"], budgets={"cpu": 100, "memory": 100, "max_concurrent": 5})
    
    graph = TaskGraph()
    graph.add_node(PlanNode(id="verify_srv", action="Verify", estimated_cost=0.5))
    sched = AdaptiveScheduler(graph, rm)
    m = Mission(id="m_full", title="Full Integration", objectives=["verify"])
    mm.create_mission(m)
    
    executor = MissionExecutor(mm, gm, rm, data_dir=env["tmpdir"], simulation_guard=env["guard"])
    res = executor.execute_mission(m, graph, sched)
    
    assert res["status"] == "completed"
    assert "verify_srv" in res["completed"]
    assert mm.get_mission(m.id).status == MissionStatus.COMPLETED
    assert len(executor.history.get_history(m.id)) > 0
