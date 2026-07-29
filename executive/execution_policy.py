"""Execution Policy Enforcement: Validates executions against active Governance policies."""
import time
import logging
from typing import Dict, Any, List, Optional
from governance.governance_manager import GovernanceManager
from governance.policy import Policy

logger = logging.getLogger(__name__)

class ExecutionPolicyEnforcer:
    """Deterministic execution gatekeeper integrated with Governance Engine.
    Every execution request must pass policy validation before proceeding."""
    
    def __init__(self, governance_mgr: GovernanceManager):
        self.governance = governance_mgr
        logger.info("ExecutionPolicyEnforcer initialized with GovernanceManager")

    def validate_execution(self, execution_context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate an execution request against all active governance policies.
        Returns structured result indicating allowance, violations, and checked policies."""
        try:
            active_policies = self.governance.get_active_policies()
            if not active_policies:
                logger.debug("No active policies. Execution allowed by default.")
                return {"allowed": True, "violations": [], "checked_policies": [], "timestamp": time.time()}

            violations = []
            checked_ids = []
            
            for policy in active_policies:
                checked_ids.append(policy.id)
                for rule in policy.rules:
                    if not self._check_rule(rule, execution_context):
                        violations.append({
                            "policy_id": policy.id,
                            "policy_name": policy.name,
                            "rule": rule,
                            "reason": f"Violated {rule.get('type', 'unknown')} rule on target '{rule.get('target')}'"
                        })

            allowed = len(violations) == 0
            logger.info("Execution validation: allowed=%s, policies_checked=%d, violations=%d", 
                        allowed, len(checked_ids), len(violations))
            return {
                "allowed": allowed,
                "violations": violations,
                "checked_policies": checked_ids,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error("Execution validation failed: %s", e)
            return {"allowed": False, "violations": [{"reason": f"Validation error: {str(e)}"}], "checked_policies": [], "timestamp": time.time()}

    def _check_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate a single policy rule against the execution context."""
        r_type = rule.get("type", "")
        target = rule.get("target", "")
        value = rule.get("value")
        ctx_val = context.get(target)

        if r_type == "constraint":
            if value == "required" and not ctx_val:
                return False
            if value == "strict" and ctx_val in ("relaxed", "disabled", False):
                return False
            if value == "sandbox_only" and context.get("execution_mode") != "sandbox":
                return False
        elif r_type == "threshold":
            if isinstance(ctx_val, (int, float)) and isinstance(value, (int, float)):
                if ctx_val > value:
                    return False
        elif r_type == "deny":
            if ctx_val == value or (isinstance(value, list) and ctx_val in value):
                return False
        elif r_type == "allow":
            if ctx_val != value and not (isinstance(value, list) and ctx_val in value):
                return False
        return True

    def register_and_enable_policy(self, policy: Policy) -> bool:
        """Convenience method to register and immediately activate a policy."""
        if self.governance.register_policy(policy):
            return self.governance.enable_policy(policy.id)
        return False

    def update_policy_rules(self, policy_id: str, new_rules: List[Dict[str, Any]]) -> bool:
        """Update rules for an existing policy and persist changes."""
        policy = self.governance.store.latest(policy_id)
        if not policy:
            return False
        policy.rules = new_rules
        policy.updated_at = time.time()
        return self.governance.store.update(policy)

    def rollback_policy(self, policy_id: str, target_version: str) -> bool:
        """Delegate rollback to GovernanceManager."""
        return self.governance.rollback_policy(policy_id, target_version)

    def get_active_policies(self) -> List[Policy]:
        return self.governance.get_active_policies()
