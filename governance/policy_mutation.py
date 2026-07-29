"""Policy Mutation Engine: Deterministic structural & parameter mutations."""
import copy
import hashlib
import logging
from typing import Dict, Any, List
from .policy import Policy

logger = logging.getLogger(__name__)

class PolicyMutation:
    """Applies deterministic mutations to policy rules, thresholds, priorities, and weights."""
    
    def mutate(self, policy: Policy, seed: str = "default") -> Policy:
        mutated = copy.deepcopy(policy)
        mutated.id = hashlib.sha256(f"{policy.id}_{seed}_mut".encode()).hexdigest()[:12]
        mutated.version = self._bump_version(policy.version)
        mutated.updated_at = __import__('time').time()
        
        rule_type = self._deterministic_choice(seed, ["parameter", "threshold", "priority", "rule", "weight"])
        
        if rule_type == "parameter" and mutated.metrics:
            self._mutate_parameter(mutated, seed)
        elif rule_type == "threshold" and mutated.rules:
            self._mutate_threshold(mutated, seed)
        elif rule_type == "priority" and mutated.metrics:
            self._mutate_priority(mutated, seed)
        elif rule_type == "rule" and mutated.rules:
            self._mutate_rule(mutated, seed)
        elif rule_type == "weight" and mutated.metrics:
            self._mutate_weight(mutated, seed)
        else:
            self._mutate_parameter(mutated, seed)
            
        mutated.description = f"{policy.description} [mutated:{rule_type}]"
        logger.info("Policy mutated: %s -> %s (%s)", policy.id, mutated.id, rule_type)
        return mutated

    def _bump_version(self, version: str) -> str:
        parts = version.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        return ".".join(parts)

    def _deterministic_choice(self, seed: str, options: List[str]) -> str:
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        return options[h % len(options)]

    def _mutate_parameter(self, policy: Policy, seed: str):
        for k in policy.metrics:
            if isinstance(policy.metrics[k], (int, float)):
                delta = (int(hashlib.md5(f"{seed}_{k}".encode()).hexdigest(), 16) % 20 - 10) / 100.0
                policy.metrics[k] = round(policy.metrics[k] * (1 + delta), 3)

    def _mutate_threshold(self, policy: Policy, seed: str):
        for rule in policy.rules:
            if rule.get("type") == "threshold" and isinstance(rule.get("value"), (int, float)):
                delta = (int(hashlib.md5(f"{seed}_th".encode()).hexdigest(), 16) % 10 - 5) / 100.0
                rule["value"] = round(rule["value"] * (1 + delta), 3)

    def _mutate_priority(self, policy: Policy, seed: str):
        priorities = ["low", "medium", "high", "critical"]
        curr = policy.metrics.get("priority", "medium")
        idx = priorities.index(curr) if curr in priorities else 1
        shift = 1 if int(hashlib.md5(f"{seed}_pr".encode()).hexdigest(), 16) % 2 == 0 else -1
        policy.metrics["priority"] = priorities[max(0, min(3, idx + shift))]

    def _mutate_rule(self, policy: Policy, seed: str):
        if len(policy.rules) > 1:
            policy.rules.pop(int(hashlib.md5(f"{seed}_rr".encode()).hexdigest(), 16) % len(policy.rules))
        else:
            policy.rules.append({"type": "constraint", "target": "safety", "value": "enhanced"})

    def _mutate_weight(self, policy: Policy, seed: str):
        if "weight" not in policy.metrics:
            policy.metrics["weight"] = 1.0
        policy.metrics["weight"] = round(policy.metrics["weight"] * (0.9 + (int(hashlib.md5(f"{seed}_wt".encode()).hexdigest(), 16) % 20) / 100.0), 3)
