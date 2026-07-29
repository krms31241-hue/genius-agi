"""Executive Dashboard: Structured summaries of missions, goals, progress, resources, health."""
import logging
from typing import Dict, Any
from .mission import MissionManager
from .goal import GoalManager
from .progress_tracker import ProgressTracker
from .resource_manager import ResourceManager
from .executive_metrics import ExecutiveMetrics
from .executive_models import GoalStatus

logger = logging.getLogger(__name__)

class ExecutiveDashboard:
    """Generates comprehensive executive state summaries."""
    def __init__(self, mission_mgr: MissionManager, goal_mgr: GoalManager,
                 tracker: ProgressTracker, resource_mgr: ResourceManager, metrics: ExecutiveMetrics):
        self.mission_mgr = mission_mgr
        self.goal_mgr = goal_mgr
        self.tracker = tracker
        self.resource_mgr = resource_mgr
        self.metrics = metrics

    def generate_summary(self) -> Dict[str, Any]:
        missions = self.mission_mgr.list_missions()
        active_mission = next((m for m in missions if m.status.value == "active"), None)
        goals = self.goal_mgr.list_goals()
        progress = self.tracker.get_progress()
        usage = self.resource_mgr.get_usage()
        health_metrics = self.metrics.compute_summary()

        planning_quality = "high" if health_metrics["avg_planning_depth"] <= 4 and health_metrics["goal_completion_rate"] >= 80 else "medium"
        if health_metrics["goal_completion_rate"] < 60:
            planning_quality = "low"

        executive_health = "optimal"
        if health_metrics["failure_rate"] > 30 or health_metrics["resource_utilization"] > 0.9:
            executive_health = "degraded"
        elif health_metrics["failure_rate"] > 15:
            executive_health = "warning"

        return {
            "current_mission": active_mission.to_dict() if active_mission else None,
            "active_goals": sum(1 for g in goals if g.status == GoalStatus.RUNNING),
            "completed_goals": sum(1 for g in goals if g.status == GoalStatus.COMPLETED),
            "blocked_goals": sum(1 for g in goals if g.status == GoalStatus.WAITING),
            "execution_progress": progress,
            "resource_usage": usage,
            "executive_health": executive_health,
            "planning_quality": planning_quality,
            "metrics_summary": health_metrics,
            "timestamp": __import__('time').time()
        }
