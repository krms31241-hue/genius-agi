"""Comprehensive tests for Counterfactual Reasoning Engine."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.world.world_model import WorldModel
from simulation.simulator import SimulationEngine
from simulation.simulation_models import SimulationAction
from executive.reasoning.counterfactual import CounterfactualEngine, CounterfactualResult

@pytest.fixture
def world():
    with tempfile.TemporaryDirectory() as tmpdir:
        wm = WorldModel(data_dir=tmpdir)
        wm.create_entity("goal", {"status": "failed", "priority": "high"}, entity_id="goal_x")
        wm.create_entity("resource", {"capacity": 100, "usage": 90}, entity_id="resource_y")
        wm.create_entity("policy", {"enabled": True, "strictness": "high"}, entity_id="policy_z")
        yield wm

@pytest.fixture
def engine(world):
    sim = SimulationEngine()
    return CounterfactualEngine(simulator=sim, world_model=world)

def test_counterfactual_analysis_basic(engine):
    actual = {"success": False, "cost": 5.0, "duration": 10.0, "risk_count": 2, "confidence": 0.4, "changes_count": 1}
    setup = [SimulationAction(action_type="update", target_entity_id="goal_x", parameters={"attributes": {"status": "completed"}}, estimated_cost=0.0, estimated_duration=0.0)]
    alt = [SimulationAction(action_type="create", parameters={"entity_type": "reward"}, estimated_cost=2.0, estimated_duration=1.0)]
    
    res = engine.analyze("What if Goal X had not failed?", setup, actual, alt)
    assert isinstance(res, CounterfactualResult)
    assert res.hypothesis == "What if Goal X had not failed?"
    assert res.alternate_outcome["success"] is True
    assert res.delta["success_changed"] == 1.0
    assert res.delta["cost"] == -3.0  # 2.0 alt - 5.0 actual
    assert "succeeded" in res.explanation

def test_resource_doubling_hypothesis(engine, world):
    actual = {"success": True, "cost": 10.0, "duration": 5.0, "risk_count": 1, "confidence": 0.8, "changes_count": 2}
    setup = [SimulationAction(action_type="update", target_entity_id="resource_y", parameters={"attributes": {"capacity": 200}}, estimated_cost=0.0, estimated_duration=0.0)]
    
    res = engine.analyze("What if Resource Y was doubled?", setup, actual)
    assert res.alternate_outcome["success"] is True
    assert res.delta["success_changed"] == 0.0
    assert res.confidence > 0.0

def test_policy_disabled_hypothesis(engine, world):
    actual = {"success": False, "cost": 8.0, "duration": 12.0, "risk_count": 3, "confidence": 0.3, "changes_count": 0}
    setup = [SimulationAction(action_type="update", target_entity_id="policy_z", parameters={"attributes": {"enabled": False}}, estimated_cost=0.0, estimated_duration=0.0)]
    alt = [SimulationAction(action_type="create", parameters={"entity_type": "bypass_token"}, estimated_cost=1.0, estimated_duration=0.5)]
    
    res = engine.analyze("What if Policy Z was disabled?", setup, actual, alt)
    assert res.delta["success_changed"] == 1.0
    assert res.delta["cost"] == -7.0
    assert res.delta["duration"] == -11.5
    assert "succeeded" in res.explanation
    assert "decreased" in res.explanation

def test_world_isolation_during_counterfactual(engine, world):
    initial_status = world.get_entity("goal_x").attributes["status"]
    actual = {"success": False, "cost": 0, "duration": 0, "risk_count": 0, "confidence": 0, "changes_count": 0}
    setup = [SimulationAction(action_type="update", target_entity_id="goal_x", parameters={"attributes": {"status": "completed"}}, estimated_cost=0.0, estimated_duration=0.0)]
    
    engine.analyze("Isolation test", setup, actual)
    assert world.get_entity("goal_x").attributes["status"] == initial_status

def test_explanation_generation(engine):
    actual = {"success": True, "cost": 5.0, "duration": 5.0, "risk_count": 0, "confidence": 0.9, "changes_count": 1}
    setup = [SimulationAction(action_type="update", target_entity_id="resource_y", parameters={"attributes": {"usage": 99}}, estimated_cost=0.0, estimated_duration=0.0)]
    alt = [SimulationAction(action_type="create", parameters={"entity_type": "heavy_task"}, estimated_cost=20.0, estimated_duration=15.0)]
    
    res = engine.analyze("Heavy load scenario", setup, actual, alt)
    assert "increased" in res.explanation
    assert "cost increased by 15.00" in res.explanation
    assert "duration increased by 10.00" in res.explanation

def test_delta_calculation_precision(engine):
    actual = {"success": True, "cost": 10.1234, "duration": 5.5555, "risk_count": 1, "confidence": 0.8, "changes_count": 2}
    setup = []
    alt = [SimulationAction(action_type="create", parameters={"entity_type": "x"}, estimated_cost=12.5, estimated_duration=6.0)]
    
    res = engine.analyze("Precision test", setup, actual, alt)
    assert abs(res.delta["cost"] - 2.3766) < 0.0001
    assert abs(res.delta["duration"] - 0.4445) < 0.0001

def test_serialization(engine):
    actual = {"success": False, "cost": 5.0, "duration": 5.0, "risk_count": 1, "confidence": 0.5, "changes_count": 0}
    setup = [SimulationAction(action_type="update", target_entity_id="goal_x", parameters={"attributes": {"status": "active"}}, estimated_cost=0.0, estimated_duration=0.0)]
    res = engine.analyze("Serialization test", setup, actual)
    data = res.to_dict()
    assert isinstance(data, dict)
    assert data["hypothesis"] == "Serialization test"
    assert isinstance(data["delta"], dict)
    assert isinstance(data["explanation"], str)
    assert "alternate_outcome" in data
