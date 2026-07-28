"""Uncertainty quantification for decisions."""
from typing import List
from .decision_models import Candidate

class UncertaintyEstimator:
    """Calculates uncertainty based on evaluator disagreement, strategy risk, and memory relevance."""
    
    def calculate(self, candidate: Candidate, evaluator_scores: List[float], memory_relevance: float) -> float:
        if not evaluator_scores:
            return 1.0
            
        mean_score = sum(evaluator_scores) / len(evaluator_scores)
        variance = sum((s - mean_score) ** 2 for s in evaluator_scores) / len(evaluator_scores)
        
        strategy_penalty = 0.2 if candidate.metadata.get("strategy_type") == "experimental" else 0.0
        memory_penalty = max(0.0, 1.0 - memory_relevance) * 0.3
        
        uncertainty = min(1.0, (variance * 2.0) + strategy_penalty + memory_penalty)
        return uncertainty
