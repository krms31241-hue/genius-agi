"""Composite scoring engine using multiple evaluators."""
from typing import Dict, Any, List
from .decision_models import Candidate
from .evaluator import BaseEvaluator

class Scorer:
    def __init__(self, evaluators: List[BaseEvaluator]):
        self.evaluators = evaluators

    def score_candidate(self, candidate: Candidate, context: Dict[str, Any]) -> Dict[str, float]:
        scores = {}
        for ev in self.evaluators:
            name = ev.__class__.__name__.replace("Evaluator", "").lower()
            scores[name] = ev.evaluate(candidate, context)
        return scores
