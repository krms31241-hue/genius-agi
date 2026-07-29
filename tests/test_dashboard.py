"""Tests for Executive Dashboard."""
import os, sys, tempfile, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.dashboard import ExecutiveDashboard
from executive.mission import MissionManager, Mission, MissionStatus
from executive.goal import GoalManager
from executive.progress_tracker import ProgressTracker
from executive.resource_manager import ResourceManager
from executive.executive_metrics import ExecutiveMetrics

def test_dashboard_generation():
    with tempfile.TemporaryDirectory() as d:
        mm = MissionManager(data_dir=d)
        gm = GoalManager(data_dir=d)
        pt = ProgressTracker()
        rm = ResourceManager(data_dir=d)
        em = ExecutiveMetrics(data_dir=d)
        mm.create_mission(Mission(id="m1", title="Active", status=MissionStatus.ACTIVE))
        pt.init_tasks(["t1", "t2"])
        dash = ExecutiveDashboard(mm, gm, pt, rm, em)
        summary = dash.generate_summary()
        assert summary["current_mission"]["id"] == "m1"
        assert summary["executive_health"] in ("optimal", "warning", "degraded")
        assert "execution_progress" in summary
