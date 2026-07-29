"""Improvement Engine: Analyzes reflection data, generates proposals, and persists lessons to Memory."""
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class ImprovementEngine:
    """Deterministic improvement proposal generator with memory integration."""
    def __init__(self, memory_adapter: Any = None):
        self.memory = memory_adapter

    def analyze_and_propose(self, report: "ReflectionReport") -> List[Dict[str, Any]]:
        """Evaluate reflection report and generate actionable improvement proposals."""
        proposals = []
        
        if report.success_rate < 0.7:
            proposals.append({
                "type": "strategy",
                "target": "execution_planning",
                "reason": "Low success rate detected",
                "action": "Increase decomposition depth and add fallback branches"
            })
        if report.efficiency_score < 0.5:
            proposals.append({
                "type": "optimization",
                "target": "resource_allocation",
                "reason": "Low execution efficiency",
                "action": "Batch low-cost tasks and adjust concurrency limits"
            })
        if report.failure_count > 2:
            proposals.append({
                "type": "reliability",
                "target": "error_handling",
                "reason": "High failure count",
                "action": "Enhance retry logic and pre-flight validation"
            })
        for mistake in report.mistakes:
            proposals.append({
                "type": "correction",
                "target": "specific_task",
                "reason": f"Mistake: {mistake}",
                "action": "Add explicit guardrail or validation step"
            })
            
        report.improvement_proposals = proposals
        self._store_lessons(report)
        logger.info("Generated %d improvement proposals for execution %s", len(proposals), report.execution_id)
        return proposals

    def _store_lessons(self, report: "ReflectionReport") -> None:
        """Persist extracted lessons to semantic memory if adapter is available."""
        if not self.memory or not report.lessons:
            return
        try:
            # Lazy import to prevent circular/top-level dependency issues
            from memory.memory_models import Fact
            for lesson in report.lessons:
                fact = Fact(
                    title=f"Lesson from {report.execution_id}",
                    content=lesson,
                    source="self_reflection",
                    confidence=0.9,
                    tags=["lesson", "reflection", "executive"]
                )
                if hasattr(self.memory, "add_fact"):
                    self.memory.add_fact(fact)
        except Exception as e:
            logger.warning("Failed to store lessons in memory: %s", e)
