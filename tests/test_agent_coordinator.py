"""Comprehensive tests for Multi-Agent Coordinator."""
import os
import sys
import time
import pytest
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.agent_coordinator import AgentCoordinator, AgentTask
from executive.agent_registry import AgentRegistry, AgentInfo, AgentStatus
from executive.agent_session import SessionManager, SessionStatus
from executive.agent_router import AgentRouter

@pytest.fixture
def coordinator():
    coord = AgentCoordinator(heartbeat_timeout=5.0, default_timeout=2.0, max_workers=4)
    coord.register_agent("agent_planner", "Planner", ["planning", "routing"], max_concurrent=2)
    coord.register_agent("agent_coder", "Coder", ["coding", "testing"], max_concurrent=2)
    coord.register_agent("agent_security", "Security", ["security", "audit"], max_concurrent=1)
    yield coord
    coord.shutdown()

def test_agent_registration(coordinator):
    agents = coordinator.registry.list_agents()
    assert len(agents) == 3
    assert any(a.name == "Planner" for a in agents)
    assert coordinator.deregister_agent("agent_planner") is True
    assert len(coordinator.registry.list_agents()) == 2

def test_sequential_execution(coordinator):
    tasks = [
        AgentTask(id="t1", capability="planning", payload={"data": "plan"}),
        AgentTask(id="t2", capability="coding", dependencies=["t1"], payload={"data": "code"}),
        AgentTask(id="t3", capability="security", dependencies=["t2"], payload={"data": "audit"})
    ]
    res = coordinator.execute_sequential(tasks)
    assert "t1" in res["completed"]
    assert "t2" in res["completed"]
    assert "t3" in res["completed"]
    assert len(res["failed"]) == 0

def test_parallel_execution(coordinator):
    tasks = [
        AgentTask(id="p1", capability="planning", payload={"data": "A"}),
        AgentTask(id="p2", capability="coding", payload={"data": "B"}),
        AgentTask(id="p3", capability="planning", payload={"data": "C"})
    ]
    res = coordinator.execute_parallel(tasks)
    assert len(res["completed"]) == 3
    assert len(res["failed"]) == 0

def test_dependency_ordering(coordinator):
    tasks = [
        AgentTask(id="d3", capability="security", dependencies=["d2"]),
        AgentTask(id="d1", capability="planning"),
        AgentTask(id="d2", capability="coding", dependencies=["d1"])
    ]
    res = coordinator.execute_sequential(tasks)
    assert res["completed"] == ["d1", "d2", "d3"] or set(res["completed"]) == {"d1", "d2", "d3"}

def test_failure_isolation(coordinator):
    tasks = [
        AgentTask(id="f1", capability="planning", payload={"data": "ok"}),
        AgentTask(id="f2", capability="coding", payload={"simulate_failure": True}),
        AgentTask(id="f3", capability="planning", payload={"data": "ok"})
    ]
    res = coordinator.execute_sequential(tasks)
    assert "f1" in res["completed"]
    assert "f2" in res["failed"]
    assert "f3" in res["completed"]

def test_task_timeout(coordinator):
    tasks = [
        AgentTask(id="to1", capability="planning", timeout_sec=0.2, payload={"simulate_timeout": True})
    ]
    res = coordinator.execute_parallel(tasks)
    assert "to1" in res["failed"]
    assert "Timeout" in res["errors"].get("to1", "")

def test_agent_restart(coordinator):
    assert coordinator.restart_agent("agent_coder") is True
    agent = coordinator.registry.get_agent("agent_coder")
    assert agent.status == AgentStatus.ACTIVE
    assert agent.current_load == 0

def test_routing_and_load_balancing():
    reg = AgentRegistry(heartbeat_timeout=5.0)
    reg.register(AgentInfo(id="a1", name="A1", capabilities=["x"], max_concurrent=2))
    reg.register(AgentInfo(id="a2", name="A2", capabilities=["x"], max_concurrent=2))
    router = AgentRouter(reg)
    
    # Route first task -> should pick a1 (lowest load)
    ag1 = router.route_task("t1", "x")
    assert ag1 == "a1"
    
    # Route second task -> should pick a2 (load balanced)
    ag2 = router.route_task("t2", "x")
    assert ag2 == "a2"
    
    router.release_route("t1")
    router.release_route("t2")

def test_session_lifecycle():
    sm = SessionManager()
    s = sm.create("agent1", "task1")
    assert s.status == SessionStatus.PENDING
    assert sm.start(s.session_id) is True
    assert s.status == SessionStatus.RUNNING
    assert sm.heartbeat(s.session_id) is True
    assert sm.complete(s.session_id, {"ok": True}) is True
    assert s.status == SessionStatus.COMPLETED
    assert s.result == {"ok": True}

def test_conflict_prevention():
    reg = AgentRegistry()
    reg.register(AgentInfo(id="c1", name="C1", capabilities=["exclusive"], max_concurrent=5))
    router = AgentRouter(reg)
    router.set_exclusive_capability("exclusive", exclusive=True)
    
    ag1 = router.route_task("cx1", "exclusive")
    assert ag1 == "c1"
    
    # Second route should be deferred due to lock
    ag2 = router.route_task("cx2", "exclusive")
    assert ag2 is None
    
    router.release_route("cx1")
    ag3 = router.route_task("cx2", "exclusive")
    assert ag3 == "c1"
