"""Policy Optimizer: Generates, scores, and filters candidate populations."""
import logging
from typing import List, Dict, Any
from .policy import Policy
from .policy_mutation import PolicyMutation

logger = logging.getLogger(__name__)

class PolicyOptimizer:
    """Generates multiple mutated candidates, scores them, and discards weak policies."""
    
    def __init__(self, population_size: int = 6, survival_rate: float = 0.5):
        self.pop_size = population_size
        self.survival_rate = survival_rate
        self.mutator = PolicyMutation()

    def optimize(self, base_policy: Policy, context: Dict[str, Any]) -> List[Policy]:
        population = [base_policy]
        for i in range(1, self.pop_size):
            population.append(self.mutator.mutate(base_policy, seed=f"opt_{i}_{base_policy.id}"))
            
        scored = []
        for p in population:
            score = self._score_candidate(p, context)
            p.score = score
            scored.append((p, score))
            
        scored.sort(key=lambda x: x[1], reverse=True)
        cutoff = max(1, int(len(scored) * self.survival_rate))
        survivors = [p for p, _ in scored[:cutoff]]
        
        logger.info("Optimization complete: %d candidates -> %d survivors", len(population), len(survivors))
        return survivors

    def _score_candidate(self, policy: Policy, context: Dict[str, Any]) -> float:
        base = 50.0
        priority_bonus = {"low": 0, "medium": 5, "high": 10, "critical": 15}.get(policy.metrics.get("priority", "medium"), 0)
        rule_bonus = len(policy.rules) * 2.0
        risk_penalty = policy.metrics.get("max_failure_rate", 0) * 50.0
        stability_bonus = 10.0 if policy.metrics.get("max_rollback_rate", 1.0) < 0.2 else 0.0
        return max(0.0, min(100.0, base + priority_bonus + rule_bonus + stability_bonus - risk_penalty))
