"""Comprehensive tests for World Model Foundation."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.world.world_model import WorldModel
from executive.world.models import WorldEntity, WorldEvent, WorldSnapshot

@pytest.fixture
def model():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield WorldModel(data_dir=tmpdir)

def test_entity_creation(model):
    e = model.create_entity("server", {"ip": "10.0.0.1"}, metadata={"env": "prod"})
    assert e.entity_type == "server"
    assert e.attributes["ip"] == "10.0.0.1"
    assert model.get_entity(e.id) is e
    assert len(model.get_history(e.id)) == 1

def test_entity_update(model):
    e = model.create_entity("db", {"status": "idle"})
    model.update_entity(e.id, {"attributes": {"status": "active"}}, source="admin", reason="start")
    updated = model.get_entity(e.id)
    assert updated.attributes["status"] == "active"
    history = model.get_history(e.id)
    assert len(history) == 2
    assert history[-1].before_state["attributes"]["status"] == "idle"
    assert history[-1].after_state["attributes"]["status"] == "active"
    assert history[-1].source == "admin"

def test_entity_deletion(model):
    e = model.create_entity("cache")
    assert model.delete_entity(e.id) is True
    assert model.get_entity(e.id) is None
    history = model.get_history(e.id)
    assert history[-1].reason == "deletion"
    assert history[-1].after_state == {}

def test_query_entities(model):
    model.create_entity("node", {"role": "worker"})
    model.create_entity("node", {"role": "master"})
    model.create_entity("service", {"role": "api"})
    workers = model.query_entities(lambda e: e.entity_type == "node" and e.attributes.get("role") == "worker")
    assert len(workers) == 1
    assert workers[0].attributes["role"] == "worker"

def test_snapshot_and_rollback(model):
    e1 = model.create_entity("app", {"version": "1.0"})
    snap1 = model.create_snapshot({"tag": "v1"})
    model.update_entity(e1.id, {"attributes": {"version": "2.0"}})
    assert model.get_entity(e1.id).attributes["version"] == "2.0"
    assert model.rollback_to_snapshot(snap1.id) is True
    assert model.get_entity(e1.id).attributes["version"] == "1.0"
    assert len(model.get_history(e1.id)) == 1

def test_snapshot_consistency(model):
    e = model.create_entity("test", {"val": 1})
    snap = model.create_snapshot()
    model.update_entity(e.id, {"attributes": {"val": 99}})
    assert snap.entities[e.id]["attributes"]["val"] == 1
    assert model.get_entity(e.id).attributes["val"] == 99

def test_serialization(model):
    e = model.create_entity("ser", {"a": 1})
    d = e.to_dict()
    restored = WorldEntity.from_dict(d)
    assert restored.id == e.id
    assert restored.attributes == e.attributes

    snap = model.create_snapshot()
    sd = snap.to_dict()
    restored_snap = WorldSnapshot.from_dict(sd)
    assert restored_snap.id == snap.id
    assert restored_snap.event_count == snap.event_count

def test_persistence(model):
    e = model.create_entity("persist", {"x": 10})
    model.update_entity(e.id, {"attributes": {"y": 20}})
    model.save()
    
    model2 = WorldModel(data_dir=model.data_dir)
    loaded = model2.get_entity(e.id)
    assert loaded is not None
    assert loaded.attributes["x"] == 10
    assert loaded.attributes["y"] == 20
    assert len(model2.get_history(e.id)) == 2

def test_event_history_ordering(model):
    e = model.create_entity("chron", {"step": 0})
    time.sleep(0.01)
    model.update_entity(e.id, {"attributes": {"step": 1}})
    time.sleep(0.01)
    model.update_entity(e.id, {"attributes": {"step": 2}})
    history = model.get_history(e.id)
    assert len(history) == 3
    assert history[0].timestamp <= history[1].timestamp <= history[2].timestamp
    assert history[0].reason == "entity_created"
    assert history[2].after_state["attributes"]["step"] == 2
