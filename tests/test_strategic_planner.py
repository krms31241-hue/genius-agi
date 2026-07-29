"""Tests for Strategic Planner."""
import os, sys, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.strategic_planner import StrategicPlanner
from executive.mission import Mission

def test_decompose():
    sp = StrategicPlanner()
    m = Mission(id="strat1", title="Expand", objectives=["market", "tech"], metadata={"scope": "global"})
    goals = sp.decompose_mission(m, depth=2)
    assert len(goals) == 6  # 2 strategic + 4 executive
    assert any(g.metadata.get("roi") for g in goals)

def test_reprioritize():
    sp = StrategicPlanner()
    goals = sp.decompose_mission(Mission(id="p1", title="P", objectives=["a"]))
    rep = sp.reprioritize(goals, {"urgency_multiplier": 2.0})
    assert rep[0].priority >= rep[-1].priority
