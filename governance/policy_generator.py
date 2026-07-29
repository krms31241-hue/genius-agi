"""Policy Generator: Creates candidate policies from system telemetry."""
import time
import hashlib
import logging
from typing import Dict, Any, List
from .policy import Policy

logger = logging.getLogger(__name__)

class PolicyGenerator:
    """Generates baseline candidate policies targeting observed system weaknesses.
    Read-only integration with memory, decision, failure, and upgrade telemetry."""
    
    def generate(self, context: Dict[str, Any]) -> List[Policy]:
        candidates = []
        mem_stats = context.get("memory_stats", {})
        dec_stats = context.get("decision_stats", {})
        fail_stats = context.get("failure_stats", {})
        upg_stats = context.get("upgrade_stats", {})
        
        # 1. Memory Recall Policy
        if mem_stats.get("recall_rate", 100) < 70:
            candidates.append(self._create_policy(
                "memory_recall_boost", "Increase semantic retrieval thresholds",
                rules=[{"type": "threshold", "target": "recall", "value": 0.75}],
                metrics={"target_recall": 0.85, "priority": "high"}
            ))
            
        # 2. Decision Confidence Policy
        if dec_stats.get("avg_confidence", 1.0) < 0.6:
            candidates.append(self._create_policy(
                "decision_confidence_guard", "Require higher consensus for execution",
                rules=[{"type": "threshold", "target": "consensus", "value": 0.7}],
                metrics={"min_confidence": 0.75, "priority": "high"}
            ))
            
        # 3. Failure Mitigation Policy
        if fail_stats.get("recent_failures", 0) > 5:
            candidates.append(self._create_policy(
                "failure_mitigation_strict", "Enforce stricter sandbox validation",
                rules=[{"type": "constraint", "target": "sandbox", "value": "strict"}],
                metrics={"max_failure_rate": 0.1, "priority": "critical"}
            ))
            
        # 4. Upgrade Stability Policy
        if upg_stats.get("rollback_rate", 0) > 0.2:
            candidates.append(self._create_policy(
                "upgrade_stability_guard", "Require extended benchmarking before activation",
                rules=[{"type": "constraint", "target": "benchmark", "value": "extended"}],
                metrics={"max_rollback_rate": 0.1, "priority": "high"}
            ))
            
        # Fallback baseline if no weaknesses detected
        if not candidates:
            candidates.append(self._create_policy(
                "baseline_optimization", "Standard operational tuning",
                rules=[{"type": "threshold", "target": "general", "value": 0.5}],
                metrics={"priority": "medium"}
            ))
            
        logger.info("Generated %d candidate policies from telemetry", len(candidates))
        return candidates

    def _create_policy(self, name: str, desc: str, rules: List[Dict], metrics: Dict) -> Policy:
        pid = hashlib.sha256(f"{name}_{time.time()}".encode()).hexdigest()[:12]
        return Policy(
            id=pid, name=name, version="1.0.0", description=desc,
            author="policy_generator", status="draft", rules=rules, metrics=metrics
        )
