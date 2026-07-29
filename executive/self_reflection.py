"""Self Reflection Engine: Post-execution analysis, lesson extraction, and improvement orchestration."""
import time
import logging
from typing import Dict, Any, List, Optional
from .reflection_report import ReflectionReport
from .improvement_engine import ImprovementEngine

logger = logging.getLogger(__name__)

class SelfReflectionEngine:
    """Orchestrates deterministic post-execution reflection and continuous improvement."""
    def __init__(self, improvement_engine: Optional[ImprovementEngine] = None):
        self.improvement_engine = improvement_engine or ImprovementEngine()
        self.latest_report: Optional[ReflectionReport] = None

    def reflect(self, execution_id: str, execution_data: Dict[str, Any], memory_adapter: Any = None) -> ReflectionReport:
        """Analyze execution outcomes, extract lessons, and generate improvement proposals."""
        completed = execution_data.get("completed", [])
        failed = execution_data.get("failed", [])
        total = len(completed) + len(failed)
        success_rate = len(completed) / max(1, total)
        failure_count = len(failed)

        # Efficiency: deterministic ratio of successful throughput to duration
        duration = max(0.01, execution_data.get("total_duration", 1.0))
        efficiency = min(1.0, (len(completed) * 0.15) / duration)

        # Mistakes: deduplicated error messages
        errors = execution_data.get("errors", {})
        mistakes = list(set(str(v) for v in errors.values() if v))

        # Lessons: rule-based extraction from outcomes
        lessons = self._extract_lessons(success_rate, failure_count, mistakes, execution_data)

        report = ReflectionReport(
            execution_id=execution_id,
            success_rate=round(success_rate, 3),
            failure_count=failure_count,
            efficiency_score=round(efficiency, 3),
            mistakes=mistakes,
            lessons=lessons,
            metadata={"total_tasks": total, "duration": duration}
        )

        # Attach memory adapter dynamically if provided
        if memory_adapter:
            self.improvement_engine.memory = memory_adapter
            
        self.improvement_engine.analyze_and_propose(report)
        self.latest_report = report
        
        logger.info("Reflection complete for %s: success=%.2f, efficiency=%.2f, proposals=%d",
                    execution_id, success_rate, efficiency, len(report.improvement_proposals))
        return report

    def _extract_lessons(self, success_rate: float, failure_count: int, mistakes: List[str], data: Dict[str, Any]) -> List[str]:
        """Deterministic lesson extraction based on execution metrics and errors."""
        lessons = []
        if success_rate >= 0.9:
            lessons.append("High success rate indicates effective planning and execution strategy.")
        elif success_rate < 0.5:
            lessons.append("Low success rate suggests over-ambitious scoping or insufficient dependency validation.")
            
        if failure_count > 0:
            lessons.append(f"Failures detected in {failure_count} tasks. Review error handling and retry thresholds.")
            
        for m in mistakes:
            m_lower = m.lower()
            if "timeout" in m_lower:
                lessons.append("Timeouts detected: Consider increasing task timeouts or optimizing long-running operations.")
            elif "resource" in m_lower or "memory" in m_lower or "budget" in m_lower:
                lessons.append("Resource constraints hit: Implement stricter resource budgeting or task batching.")
            elif "dependency" in m_lower or "cycle" in m_lower:
                lessons.append("Dependency issues detected: Validate DAG structure and enforce topological ordering.")
                
        if not lessons:
            lessons.append("Execution completed within normal parameters. Continue monitoring for optimization opportunities.")
        return lessons

    def get_latest_report(self) -> Optional[ReflectionReport]:
        return self.latest_report
