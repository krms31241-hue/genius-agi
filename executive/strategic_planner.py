"""Strategic Planner: Converts missions into strategic goals with ROI/Risk/Cost/Impact/Time estimates."""
import hashlib
import time
import logging
from typing import List, Dict, Any
from .mission import Mission
from .executive_models import Goal, GoalStatus

logger = logging.getLogger(__name__)

class StrategicPlanner:
    """Transforms long-term missions into executable strategic goals with deterministic estimates."""
    def __init__(self, base_roi: float = 1.5, base_risk: float = 0.3):
        self.base_roi = base_roi
        self.base_risk = base_risk

    def decompose_mission(self, mission: Mission, depth: int = 2) -> List[Goal]:
        """Break mission into strategic goals, then into executive goals."""
        strategic_goals = []
        for i, obj in enumerate(mission.objectives):
            gid = hashlib.sha256(f"{mission.id}_strat_{i}".encode()).hexdigest()[:12]
            estimates = self._estimate(obj, mission.metadata)
            strategic_goals.append(Goal(
                id=gid, title=f"Strategic: {obj}", description=f"Achieve {obj} for mission {mission.title}",
                importance=estimates["impact"], urgency=estimates["time_pressure"],
                status=GoalStatus.PLANNED, origin="strategic_planner",
                parent_goal=mission.id, metadata={
                    "roi": estimates["roi"], "risk": estimates["risk"],
                    "cost": estimates["cost"], "impact": estimates["impact"],
                    "time_estimate": estimates["time"], "mission_id": mission.id
                }
            ))

        executive_goals = []
        for sg in strategic_goals:
            for j in range(depth):
                eid = hashlib.sha256(f"{sg.id}_exec_{j}".encode()).hexdigest()[:12]
                executive_goals.append(Goal(
                    id=eid, title=f"Execute phase {j+1} of {sg.title}",
                    description=f"Operational step {j+1} for {sg.title}",
                    importance=sg.importance * 0.9, urgency=sg.urgency,
                    status=GoalStatus.NEW, origin="strategic_planner",
                    parent_goal=sg.id, dependencies=[sg.id] if j == 0 else [executive_goals[-1].id],
                    metadata={"atomic": True, "risk": sg.metadata["risk"] * 1.1, "resource_cost": sg.metadata["cost"] / depth}
                ))
        logger.info("Decomposed mission %s into %d strategic and %d executive goals", mission.id, len(strategic_goals), len(executive_goals))
        return strategic_goals + executive_goals

    def reprioritize(self, goals: List[Goal], context: Dict[str, Any] = None) -> List[Goal]:
        """Dynamic reprioritization based on context and estimates."""
        context = context or {}
        urgency_boost = context.get("urgency_multiplier", 1.0)
        for g in goals:
            roi = g.metadata.get("roi", 1.0)
            risk = g.metadata.get("risk", 0.5)
            impact = g.metadata.get("impact", 0.5)
            time_est = g.metadata.get("time_estimate", 1.0)
            score = (roi * impact * urgency_boost) / (risk * time_est + 0.1)
            g.priority = max(0.0, min(100.0, score * 10.0))
            g.updated_at = time.time()
        goals.sort(key=lambda x: x.priority, reverse=True)
        return goals

    def _estimate(self, objective: str, mission_meta: Dict[str, Any]) -> Dict[str, float]:
        h = int(hashlib.md5(objective.encode()).hexdigest(), 16)
        return {
            "roi": self.base_roi + (h % 100) / 100.0,
            "risk": min(1.0, self.base_risk + (h % 50) / 100.0),
            "cost": 1.0 + (h % 200) / 50.0,
            "impact": 0.5 + (h % 50) / 100.0,
            "time": 1.0 + (h % 300) / 100.0,
            "time_pressure": min(1.0, 1.0 / (1.0 + (h % 300) / 100.0))
        }
