"""Structured reasoning generator for decisions."""
from typing import List, Dict, Any
from .decision_models import Candidate

class ExplanationEngine:
    """Generates transparent, structured reasoning for every decision."""
    
    def generate(self, candidate: Candidate, scores: Dict[str, float], risk: Dict[str, float],
                 confidence: float, uncertainty: float, rule_violations: List[str],
                 consensus_score: float) -> List[str]:
        reasons = []
        if rule_violations:
            reasons.append(f"Rejected due to hard constraint violations: {', '.join(rule_violations)}")
            return reasons
            
        reasons.append(f"Selected strategy '{candidate.metadata.get('strategy_type', 'unknown')}' with consensus score {consensus_score:.2f}")
        reasons.append(f"Estimated benefit: {scores.get('benefit', 0):.2f}, alignment: {scores.get('alignment', 0):.2f}")
        reasons.append(f"Risk assessment: failure_prob={risk.get('failure_probability', 0):.2f}, security_impact={risk.get('security_impact', 0):.2f}")
        reasons.append(f"Confidence: {confidence:.2f} | Uncertainty: {uncertainty:.2f}")
        
        if uncertainty > 0.5:
            reasons.append("High uncertainty detected due to low memory relevance or evaluator disagreement.")
        if risk.get('composite_risk', 0) > 0.6:
            reasons.append("Elevated risk profile requires sandbox validation before execution.")
            
        return reasons
