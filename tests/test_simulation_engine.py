"""Comprehensive tests for Simulation Engine Core."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.world.world_model import WorldModel
from simulation.simulator import SimulationEngine
from simulation.simulation_models import SimulationAction, SimulationPlan
from simulation.simulation_result import SimulationResult

@pytest.fixture
def world():
    with tempfile.TemporaryDirectory() as tmpdir:
        wm = WorldModel(data_dir=tmpdir)
        wm.create_entity("server", {"ip": "10.0.0.1"})
        wm.create_entity("db", {"port": 5432})
        yield wm

def test_world_isolation(world):
    """Real world must remain completely unchanged after simulation."""
    engine = SimulationEngine()
    initial_count = len(world.state.entities)
    initial_ips = {e.attributes.get("ip") for e in world.state.entities.values()}
    
    action = SimulationAction(action_type="create", parameters={"entity_type": "test", "attributes": {"x": 1}})
    res = engine.simulate(action, world)
    
    assert res.success is True
    assert len(world.state.entities) == initial_count
    assert {e.attributes.get("ip") for e in world.state.entities.values()} == initial_ips

def test_multiple_simulations(world):
    """Simulating a list of actions must track all changes sequentially."""
    engine = SimulationEngine()
    target_id = list(world.state.entities.keys())[0]
    actions = [
        SimulationAction(action_type="create", parameters={"entity_type": "cache"}),
        SimulationAction(action_type="update", target_entity_id=target_id, parameters={"attributes": {"ip": "10.0.0.2"}})
    ]
    res = engine.simulate(actions, world)
    assert res.success is True
    assert len(res.predicted_changes) == 2
    assert world.get_entity(target_id).attributes.get("ip") == "10.0.0.1"  # Real world unchanged

def test_rollback_safety(world):
    """Rollback flag must be true when changes are tracked."""
    engine = SimulationEngine()
    target_id = list(world.state.entities.keys())[0]
    action = SimulationAction(action_type="delete", target_entity_id=target_id)
    res = engine.simulate(action, world)
    assert res.success is True
    assert res.rollback_possible is True
    assert len(res.predicted_changes) == 1

def test_confidence_calculation(world):
    """Confidence must decrease proportionally to predicted risks."""
    engine = SimulationEngine()
    res_valid = engine.simulate(SimulationAction(action_type="create", parameters={"entity_type": "t"}), world)
    assert res_valid.confidence > 0.8
    
    res_risky = engine.simulate(SimulationAction(action_type="update", target_entity_id="nonexistent", parameters={}), world)
    assert res_risky.success is False
    assert res_risky.confidence < res_valid.confidence
    assert len(res_risky.predicted_risks) == 1

def test_prediction_integrity(world):
    """Predicted changes must accurately reflect simulated operations."""
    engine = SimulationEngine()
    target_id = list(world.state.entities.keys())[0]
    action = SimulationAction(action_type="update", target_entity_id=target_id, parameters={"attributes": {"status": "active"}})
    res = engine.simulate(action, world)
    
    assert res.success is True
    assert any(c["target"] == target_id and c["type"] == "update" for c in res.predicted_changes)
    assert world.get_entity(target_id).attributes.get("status") is None

def test_simulate_plan(world):
    """SimulationPlan must execute all contained actions and aggregate metrics."""
    engine = SimulationEngine()
    plan = SimulationPlan(actions=[
        SimulationAction(action_type="create", parameters={"entity_type": "node"}, estimated_cost=2.0, estimated_duration=1.5),
        SimulationAction(action_type="create", parameters={"entity_type": "link"}, estimated_cost=1.0, estimated_duration=0.5)
    ])
    res = engine.simulate(plan, world)
    assert res.success is True
    assert len(res.predicted_changes) == 2
    assert res.estimated_cost == 3.0
    assert res.estimated_duration == 2.0

def test_serialization(world):
    """SimulationResult must serialize cleanly to dictionary."""
    engine = SimulationEngine()
    res = engine.simulate(SimulationAction(action_type="create", parameters={"entity_type": "x"}), world)
    data = res.to_dict()
    assert isinstance(data, dict)
    assert data["success"] is True
    assert isinstance(data["predicted_changes"], list)
    assert isinstance(data["confidence"], float)
    assert "rollback_possible" in data
