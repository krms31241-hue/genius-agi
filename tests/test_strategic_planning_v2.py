"""Comprehensive tests for Strategic Planning Engine."""
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from planner.strategic_planner import StrategicPlanningEngine, PlanningAction, StrategicPlan

@pytest.fixture
def engine():
    return StrategicPlanningEngine(min_action_cost=1.0)

@pytest.fixture
def sample_actions():
    return [
        PlanningAction(id="a1", name="gather_resources", prerequisites=set(), effects={"wood", "stone"}, cost=2.0),
        PlanningAction(id="a2", name="craft_tools", prerequisites={"wood"}, effects={"tools"}, cost=3.0),
        PlanningAction(id="a3", name="build_shelter", prerequisites={"tools", "stone"}, effects={"shelter"}, cost=5.0),
        PlanningAction(id="a4", name="light_fire", prerequisites={"wood"}, effects={"fire"}, cost=1.0),
        PlanningAction(id="a5", name="cook_food", prerequisites={"fire", "tools"}, effects={"food"}, cost=2.0),
        PlanningAction(id="dead_end", name="useless_step", prerequisites={"shelter"}, effects={"decoration"}, cost=10.0)
    ]

def test_goal_splitting(engine):
    rules = {
        "survive": ["shelter", "food", "fire"],
        "shelter": ["build_shelter"],
        "food": ["cook_food"]
    }
    subgoals = engine.split_goal("survive", rules)
    assert set(subgoals) == {"build_shelter", "cook_food", "fire"}
    assert len(subgoals) == 3

def test_astar_planning(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"shelter", "food"},
        actions=sample_actions,
        algorithm="astar"
    )
    assert plan.metadata["status"] == "success"
    assert "shelter" in plan.topological_order or any("shelter" in a.effects for a in plan.actions)
    assert plan.total_cost > 0
    assert len(plan.actions) >= 4  # gather, craft, build, light, cook

def test_greedy_planning(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"fire"},
        actions=sample_actions,
        algorithm="greedy"
    )
    assert plan.metadata["status"] == "success"
    action_names = [a.name for a in plan.actions]
    assert "gather_resources" in action_names
    assert "light_fire" in action_names

def test_beam_search_planning(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"shelter"},
        actions=sample_actions,
        algorithm="beam",
        beam_width=2
    )
    assert plan.metadata["status"] == "success"
    assert len(plan.topological_order) == len(plan.actions)

def test_dag_construction_and_ordering(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"food"},
        actions=sample_actions,
        algorithm="astar"
    )
    # Verify topological order respects dependencies
    action_map = {a.id: a for a in plan.actions}
    for i, aid in enumerate(plan.topological_order):
        action = action_map[aid]
        for prereq in action.prerequisites:
            # Find producer of prereq
            for prev_aid in plan.topological_order[:i]:
                if prereq in action_map[prev_aid].effects:
                    assert plan.topological_order.index(prev_aid) < i

def test_prune_impossible_branches(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"shelter"},
        actions=sample_actions,
        algorithm="astar"
    )
    action_ids = [a.id for a in plan.actions]
    # dead_end produces 'decoration' which is not needed for 'shelter'
    assert "dead_end" not in action_ids
    assert all(a.name != "useless_step" for a in plan.actions)

def test_cost_optimization(engine):
    actions = [
        PlanningAction(id="fast", name="fast_route", prerequisites=set(), effects={"goal"}, cost=5.0),
        PlanningAction(id="slow", name="slow_route", prerequisites=set(), effects={"goal"}, cost=10.0),
        PlanningAction(id="prep", name="prep", prerequisites=set(), effects={"boost"}, cost=1.0),
        PlanningAction(id="boosted", name="boosted_route", prerequisites={"boost"}, effects={"goal"}, cost=2.0)
    ]
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"goal"},
        actions=actions,
        algorithm="astar"
    )
    # A* should find prep + boosted_route (cost 3.0) over fast_route (5.0)
    assert plan.total_cost == 3.0
    action_names = [a.name for a in plan.actions]
    assert "prep" in action_names
    assert "boosted_route" in action_names

def test_no_path_found(engine):
    actions = [
        PlanningAction(id="x", name="step1", prerequisites={"missing"}, effects={"y"}, cost=1.0)
    ]
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"y"},
        actions=actions,
        algorithm="astar"
    )
    assert plan.metadata["status"] == "failed"
    assert len(plan.actions) == 0

def test_serialization(engine, sample_actions):
    plan = engine.plan(
        initial_state=set(),
        goal_conditions={"fire"},
        actions=sample_actions,
        algorithm="greedy"
    )
    data = plan.to_dict()
    assert isinstance(data, dict)
    assert "dag" in data
    assert "topological_order" in data
    assert isinstance(data["actions"], list)
    assert data["metadata"]["status"] == "success"

def test_max_iterations_cutoff(engine):
    # Create a scenario that requires many steps to force iteration limit
    actions = [PlanningAction(id=f"s{i}", name=f"step{i}", prerequisites={f"s{i-1}" if i>0 else "start"}, effects={f"s{i}"}, cost=1.0) for i in range(50)]
    plan = engine.plan(
        initial_state={"start"},
        goal_conditions={"s49"},
        actions=actions,
        algorithm="astar",
        max_iterations=10
    )
    assert plan.metadata["status"] == "failed"
