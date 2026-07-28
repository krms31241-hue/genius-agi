"""Policy Engine: Registration, evaluation, validation, comparison, and rollback."""
import time
import logging
from typing import List, Dict, Any, Optional
from .policy import Policy
from .core_axioms import CoreAxiom
from .policy_store import PolicyStore

logger = logging.getLogger(__name__)

class PolicyEngine:
    def __init__(self, store: PolicyStore, axioms: List[CoreAxiom]):
        self.store = store
        self.axioms = {a.id: a for a in axioms if a.enabled}

    def register_policy(self, policy: Policy) -> bool:
        if not self.validate(policy):
            logger.warning("Policy registration failed validation: %s", policy.id)
            return False
        policy.status = "draft"
        return self.store.add(policy)

    def enable_policy(self, policy_id: str) -> bool:
        policy = self.store.latest(policy_id)
        if not policy:
            return False
        policy.status = "active"
        policy.updated_at = time.time()
        success = self.store.update(policy)
        if success:
            logger.info("Policy enabled: %s", policy_id)
        return success

    def disable_policy(self, policy_id: str) -> bool:
        policy = self.store.latest(policy_id)
        if not policy:
            return False
        policy.status = "disabled"
        policy.updated_at = time.time()
        success = self.store.update(policy)
        if success:
            logger.info("Policy disabled: %s", policy_id)
        return success

    def evaluate(self, policy: Policy, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        violations = []
        for axiom in self.axioms.values():
            if not self._check_axiom_compliance(policy, axiom, context):
                violations.append(axiom.id)
        score = max(0.0, 100.0 - (len(violations) * 25.0))
        policy.score = score
        logger.info("Policy evaluated: %s | Score: %.1f | Violations: %d", policy.id, score, len(violations))
        return {"policy_id": policy.id, "score": score, "violations": violations, "compliant": len(violations) == 0}

    def validate(self, policy: Policy) -> bool:
        if not policy.id or not policy.name:
            return False
        if policy.status not in ("draft", "active", "disabled", "archived"):
            return False
        return True

    def compare(self, policy_a: Policy, policy_b: Policy) -> Dict[str, Any]:
        diff = {"id": policy_a.id, "changes": []}
        if policy_a.version != policy_b.version:
            diff["changes"].append(f"version: {policy_a.version} -> {policy_b.version}")
        if policy_a.status != policy_b.status:
            diff["changes"].append(f"status: {policy_a.status} -> {policy_b.status}")
        if policy_a.rules != policy_b.rules:
            diff["changes"].append("rules modified")
        if policy_a.metrics != policy_b.metrics:
            diff["changes"].append("metrics modified")
        logger.info("Policy compared: %s | Changes: %d", policy_a.id, len(diff["changes"]))
        return diff

    def rollback(self, policy_id: str, target_version: str) -> bool:
        return self.store.rollback(policy_id, target_version)

    def _check_axiom_compliance(self, policy: Policy, axiom: CoreAxiom, context: Dict[str, Any]) -> bool:
        if axiom.id == "axiom_rollback" and "no_rollback" in policy.name.lower():
            return False
        if axiom.id == "axiom_tests" and policy.metrics.get("test_pass_rate", 100) < 90:
            return False
        if axiom.id == "axiom_stability" and policy.metrics.get("stability_risk", 0) > 0.7:
            return False
        return True
