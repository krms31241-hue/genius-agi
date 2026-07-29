"""Integration tests for Executive Stage 2."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.executive_engine import ExecutiveEngine
from executive.mission import Mission

def test_strategic_pipeline():
    with tempfile.TemporaryDirectory() as d:
        engine = ExecutiveEngine(data_dir=d)
        m = Mission(id="int_m1", title="Integration", objectives=["scale", "optimize"])
        res = engine.run_strategic_pipeline(m, {"urgency_multiplier": 1.5})
        assert res["status"] == "success"
        assert res["strategic_goals"] > 0
        assert res["tasks_scheduled"] > 0
        assert len(res["meta_proposals"]) >= 0
        assert res["dashboard"]["current_mission"]["id"] == "int_m1"

def test_backward_compatibility():
    with tempfile.TemporaryDirectory() as d:
        engine = ExecutiveEngine(data_dir=d)
        res = engine.run_pipeline({"memory_stats": {"recall_rate": 90}})
        assert res["status"] == "success"
        assert "goals_generated" in res
