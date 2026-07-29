"""Tests for Executive Metrics."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.executive_metrics import ExecutiveMetrics

@pytest.fixture
def em():
    with tempfile.TemporaryDirectory() as d:
        yield ExecutiveMetrics(data_dir=d)

def test_recording_and_summary(em):
    em.update_mission(completed=2, failed=1)
    em.update_goal(completed=5, failed=2)
    em.record_planning(3)
    em.record_latency(1.5)
    em.record_recovery(True)
    em.record_decision_confidence(0.8)
    em.record_resource_utilization(0.6)
    s = em.compute_summary()
    assert s["mission_success_rate"] == pytest.approx(66.66, abs=0.1)
    assert s["goal_completion_rate"] == pytest.approx(71.42, abs=0.1)
    assert s["avg_planning_depth"] == 3.0
    assert s["recovery_rate"] == 100.0
