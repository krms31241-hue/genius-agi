"""Tests for Mission Manager."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.mission import Mission, MissionStatus, MissionManager

@pytest.fixture
def mgr():
    with tempfile.TemporaryDirectory() as d:
        yield MissionManager(data_dir=d)

def test_create_and_get(mgr):
    m = Mission(id="m1", title="Alpha", description="Test mission", objectives=["obj1"])
    assert mgr.create_mission(m) is True
    loaded = mgr.get_mission("m1")
    assert loaded.title == "Alpha"
    assert loaded.status == MissionStatus.DRAFT

def test_transitions(mgr):
    m = Mission(id="m2", title="Beta", status=MissionStatus.DRAFT)
    mgr.create_mission(m)
    assert mgr.transition_status(m, MissionStatus.ACTIVE) is True
    assert m.status == MissionStatus.ACTIVE
    assert mgr.transition_status(m, MissionStatus.DRAFT) is False

def test_statistics(mgr):
    mgr.create_mission(Mission(id="s1", title="S1", status=MissionStatus.COMPLETED))
    mgr.create_mission(Mission(id="s2", title="S2", status=MissionStatus.FAILED))
    mgr.create_mission(Mission(id="s3", title="S3", status=MissionStatus.ACTIVE))
    stats = mgr.get_statistics()
    assert stats["total"] == 3
    assert stats["completed"] == 1
    assert stats["success_rate"] == 50.0
