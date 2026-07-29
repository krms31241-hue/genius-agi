"""Goal Priority Engine."""
import logging
from typing import List
from .executive_models import Goal

logger = logging.getLogger(__name__)

class GoalPriorityEngine:
    """Scores and normalizes goal priority based on multi-factor analysis."""
    def __init__(self, weights: dict = None):
        self.w = weights or {
            "importance": 0.25, "urgency": 0.20, "risk": 0.15,
            "expected_value": 0.15, "resources": 0.10, "dep_weight": 0.05, "confidence": 0.10
        }

    def score_goals(self, goals: List[Goal]) -> List[Goal]:
        for g in goals:
            raw = (g.importance * self.w["importance"] +
                   g.urgency * self.w["urgency"] +
                   g.metadata.get("risk", 0.5) * self.w["risk"] +
                   g.metadata.get("expected_value", 0.5) * self.w["expected_value"] +
                   (1.0 - g.metadata.get("resource_cost", 0.5)) * self.w["resources"] +
                   (1.0 / (1 + len(g.dependencies))) * self.w["dep_weight"] +
                   g.metadata.get("confidence", 0.7) * self.w["confidence"])
            g.priority = max(0.0, min(100.0, raw * 100.0))
            g.updated_at = __import__('time').time()
        goals.sort(key=lambda x: x.priority, reverse=True)
        logger.info("Prioritized %d goals", len(goals))
        return goals
