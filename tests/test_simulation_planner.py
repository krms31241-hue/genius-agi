"""Comprehensive tests for Simulation Planner (What-If Planning)."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.world.world_model import WorldModel
from simulation.simulation_models import SimulationPlan, SimulationAction
from planner.simulation_planner import SimulationPlanner, WhatIfResult, PlanEvaluation

@pytest.fixture
def world():
    with tempfile.TemporaryDirectory() as tmpdir:
        wm = WorldModel(data_dir=tmpdir)
        wm.create_entity("server", {"status": "idle"})
        yield wm

def test_evaluate_multiple_futures(world):
    planner = SimulationPlanner()
    plans = [
        SimulationPlan(id="plan_A", actions=[
            SimulationAction(action_type="create", parameters={"entity_type": "cache"}, estimated_cost=5.0, estimated_duration=2.0)
        ], metadata={"goal_alignment": 0.9}),
        SimulationPlan(id="plan_B", actions=[
            SimulationAction(action_type="update", target_entity_id="nonexistent", parameters={})
        ], metadata={"goal_alignment": 0.8}),
        SimulationPlan(id="plan_C", actions=[
            SimulationAction(action_type="create", parameters={"entity_type": "db"}, estimated_cost=1.0, estimated_duration=0.5)
        ], metadata={"goal_alignment": 0.6})
    ]
    res = planner.evaluate_futures(plans, world)
    assert isinstance(res, WhatIfResult)
    assert len(res.evaluations) == 3
    assert res.best_plan is not None
    assert res.worst_plan is not None
    # Plan B fails simulation, so it should be ranked worst
    assert res.worst_plan.plan_id == "plan_B"

def test_scoring_and_ranking(world):
    planner = SimulationPlanner()
    p1 = SimulationPlan(id="high_reward", actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "x"}, estimated_cost=10.0, estimated_duration=5.0)
    ], metadata={"goal_alignment": 1.0})
    p2 = SimulationPlan(id="low_risk", actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "y"}, estimated_cost=1.0, estimated_duration=0.5)
    ], metadata={"goal_alignment": 0.4})
    
    res = planner.evaluate_futures([p1, p2], world)
    assert res.highest_reward.plan_id == "high_reward"
    # Both have 0 risks, tie-break by ID
    assert res.lowest_risk.plan_id in ["high_reward", "low_risk"]
    assert res.best_plan.plan_id in ["high_reward", "low_risk"]

def test_world_isolation_during_planning(world):
    planner = SimulationPlanner()
    initial_count = len(world.state.entities)
    plans = [SimulationPlan(actions=[SimulationAction(action_type="create", parameters={"entity_type": "test"})])]
    planner.evaluate_futures(plans, world)
    assert len(world.state.entities) == initial_count

def test_whatif_result_serialization(world):
    planner = SimulationPlanner()
    plans = [SimulationPlan(id="ser_plan", actions=[SimulationAction(action_type="create", parameters={"entity_type": "z"})])]
    res = planner.evaluate_futures(plans, world)
    data = res.to_dict()
    assert data["best_plan"] == "ser_plan"
    assert isinstance(data["evaluations"], list)
    assert "composite_score" in data["evaluations"][0]

def test_empty_plans_handling(world):
    planner = SimulationPlanner()
    res = planner.evaluate_futures([], world)
    assert len(res.evaluations) == 0
    assert res.best_plan is None
    assert res.worst_plan is None

def test_action_list_input(world):
    """Planner must accept raw List[SimulationAction] and wrap automatically."""
    planner = SimulationPlanner()
    actions = [
        SimulationAction(action_type="create", parameters={"entity_type": "node"}, estimated_cost=2.0),
        SimulationAction(action_type="create", parameters={"entity_type": "link"}, estimated_cost=1.0)
    ]
    res = planner.evaluate_futures([actions], world)
    assert len(res.evaluations) == 1
    assert res.evaluations[0].result.success is True
    assert res.evaluations[0].result.estimated_cost == 3.0

def test_risk_scoring(world):
    """Plans with predicted risks must score lower on risk dimension."""
    planner = SimulationPlanner()
    safe_plan = SimulationPlan(id="safe", actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "a"})
    ])
    risky_plan = SimulationPlan(id="risky", actions=[
        SimulationAction(action_type="update", target_entity_id="missing_1", parameters={}),
        SimulationAction(action_type="update", target_entity_id="missing_2", parameters={})
    ])
    res = planner.evaluate_futures([safe_plan, risky_plan], world)
    safe_eval = next(e for e in res.evaluations if e.plan_id == "safe")
    risky_eval = next(e for e in res.evaluations if e.plan_id == "risky")
    assert safe_eval.scores["risk"] > risky_eval.scores["risk"]
    assert res.lowest_risk.plan_id == "safe"

def test_custom_weights(world):
    """Custom weights must alter composite ranking."""
    # Heavily weight execution time
    planner = SimulationPlanner(weights={
        "goal_alignment": 0.1, "resource_usage": 0.1, "risk": 0.1,
        "execution_time": 0.6, "success_probability": 0.1
    })
    slow_plan = SimulationPlan(id="slow", actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "x"}, estimated_duration=10.0)
    ], metadata={"goal_alignment": 1.0})
    fast_plan = SimulationPlan(id="fast", actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "y"}, estimated_duration=0.1)
    ], metadata={"goal_alignment": 0.5})
    
    res = planner.evaluate_futures([slow_plan, fast_plan], world)
    assert res.best_plan.plan_id == "fast"
