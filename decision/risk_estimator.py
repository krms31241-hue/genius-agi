"""Risk estimation engine for candidate decisions."""
from typing import Dict, Any
from .decision_models import Candidate

class RiskEstimator:
    """Estimates failure probability, irreversible damage, security impact, and resource usage."""
    
    def estimate(self, candidate: Candidate, context: Dict[str, Any]) -> Dict[str, float]:
        meta = candidate.metadata
        strategy = meta.get("strategy_type", "standard")
        
        base_risk = {"standard": 0.2, "conservative": 0.1, "experimental": 0.6, "defer": 0.05}
        failure_prob = base_risk.get(strategy, 0.3)
        
        irreversible = 0.8 if meta.get("irreversible") else 0.1
        security_impact = 0.9 if context.get("security_risk") == "high" else 0.2
        resource_usage = min(1.0, meta.get("estimated_cost", 50) / 100.0)
        
        composite = (failure_prob * 0.4 + irreversible * 0.3 + security_impact * 0.2 + resource_usage * 0.1)
        
        return {
            "failure_probability": failure_prob,
            "irreversible_damage": irreversible,
            "security_impact": security_impact,
            "resource_usage": resource_usage,
            "composite_risk": min(1.0, composite)
        }
