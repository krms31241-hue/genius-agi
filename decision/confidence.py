"""Confidence estimation for decisions."""
from .decision_models import Candidate

class ConfidenceEstimator:
    """Derives confidence from risk, uncertainty, and rule compliance."""
    
    def calculate(self, candidate: Candidate, risk: float, uncertainty: float, rule_passed: bool) -> float:
        if not rule_passed:
            return 0.0
        base = 1.0 - risk
        confidence = base * (1.0 - uncertainty)
        return max(0.0, min(1.0, confidence))
