"""Consensus aggregation layer for evaluator scores."""
import math
from typing import List

class ConsensusEngine:
    """Aggregates independent evaluator scores into a consensus value.
    Penalizes high disagreement to ensure safe alignment."""
    
    def aggregate(self, evaluator_scores: List[float], weights: List[float] = None) -> float:
        if not evaluator_scores:
            return 0.0
        if weights is None or len(weights) != len(evaluator_scores):
            weights = [1.0] * len(evaluator_scores)
            
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
            
        weighted_sum = sum(s * w for s, w in zip(evaluator_scores, weights))
        consensus = weighted_sum / total_weight
        
        mean = consensus
        variance = sum((s - mean) ** 2 for s in evaluator_scores) / len(evaluator_scores)
        disagreement_penalty = math.sqrt(variance) * 0.5
        
        return max(0.0, min(1.0, consensus - disagreement_penalty))
