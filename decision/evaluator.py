"""Independent evaluators for candidate scoring."""
from abc import ABC, abstractmethod
from typing import Dict, Any
from .decision_models import Candidate

class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(self, candidate: Candidate, context: Dict[str, Any]) -> float:
        pass

class BenefitEvaluator(BaseEvaluator):
    def evaluate(self, candidate: Candidate, context: Dict[str, Any]) -> float:
        strategy = candidate.metadata.get("strategy_type", "standard")
        benefits = {"standard": 0.6, "conservative": 0.4, "experimental": 0.8, "defer": 0.1}
        return benefits.get(strategy, 0.5)

class AlignmentEvaluator(BaseEvaluator):
    def evaluate(self, candidate: Candidate, context: Dict[str, Any]) -> float:
        goal = context.get("goal", "")
        action = candidate.action.lower()
        return 0.9 if goal.lower() in action else 0.5

class CostEvaluator(BaseEvaluator):
    def evaluate(self, candidate: Candidate, context: Dict[str, Any]) -> float:
        cost = candidate.metadata.get("estimated_cost", 50)
        return max(0.0, 1.0 - (cost / 100.0))
