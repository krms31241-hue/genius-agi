"""Tests for Meta Executive."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.meta_executive import MetaExecutive
from executive.executive_metrics import ExecutiveMetrics

def test_analysis():
    with tempfile.TemporaryDirectory() as d:
        em = ExecutiveMetrics(data_dir=d)
        em.update_goal(completed=1, failed=5) # High failure
        em.record_planning(8) # Deep planning
        meta = MetaExecutive(em)
        proposals = meta.analyze()
        assert len(proposals) >= 2
        targets = [p["target"] for p in proposals]
        assert "goal_execution" in targets
        assert "planning_depth" in targets
