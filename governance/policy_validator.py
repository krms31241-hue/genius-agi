"""Policy Validator: Enforces axioms, stability, and regression guards."""
import logging
from typing import Dict, Any, List
from .policy import Policy
from .core_axioms import CoreAxiom

logger = logging.getLogger(__name__)

class PolicyValidator:
    """Rejects policies that violate core axioms, reduce stability, or cause regression."""
    
    def __init__(self, axioms: List[CoreAxiom], baseline_metrics: Dict[str, float] = None):
        self.axioms = [a for a in axioms if a.enabled]
        self.baseline = baseline_metrics or {
            "test_success": 0.95,
            "stability": 0.85,
            "failure_rate": 0.15
        }

    def validate(self, policy: Policy, sim_metrics: Dict[str, float]) -> Dict[str, Any]:
        violations = []
        reasons = []
        
        # 1. Axiom Compliance
        for axiom in self.axioms:
            if not self._check_axiom(policy, sim_metrics, axiom):
                violations.append(axiom.id)
                reasons.append(f"Violates axiom: {axiom.title}")
                
        # 2. Test Success Guard
        if sim_metrics.get("failure_rate", 0) > self.baseline["failure_rate"]:
            violations.append("axiom_tests")
            reasons.append("Increases failure rate beyond baseline")
            
        # 3. Stability Guard
        if sim_metrics.get("stability", 1) < self.baseline["stability"]:
            violations.append("axiom_stability")
            reasons.append("Reduces system stability below baseline")
            
        # 4. Regression Guard
        if sim_metrics.get("rollback_rate", 0) > 0.4:
            violations.append("regression_guard")
            reasons.append("Excessive rollback rate indicates regression")
            
        passed = len(violations) == 0
        logger.info("Validation %s for %s | Violations: %d", "PASSED" if passed else "FAILED", policy.id, len(violations))
        return {"passed": passed, "violations": violations, "reasons": reasons}

    def _check_axiom(self, policy: Policy, metrics: Dict[str, float], axiom: CoreAxiom) -> bool:
        if axiom.id == "axiom_rollback" and "no_rollback" in policy.name.lower():
            return False
        if axiom.id == "axiom_knowledge" and policy.metrics.get("delete_memory", False):
            return False
        if axiom.id == "axiom_capability" and metrics.get("performance", 1) < 0.3:
            return False
        return True
