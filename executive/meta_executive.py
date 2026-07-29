"""Meta Executive: Observes behavior, detects weaknesses, produces improvement proposals."""
import logging
from typing import Dict, Any, List
from .executive_metrics import ExecutiveMetrics
from .task_graph import TaskGraph

logger = logging.getLogger(__name__)

class MetaExecutive:
    """Analyzes executive performance and generates deterministic improvement proposals."""
    def __init__(self, metrics: ExecutiveMetrics):
        self.metrics = metrics

    def analyze(self, graph: TaskGraph = None, scheduler_state: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        summary = self.metrics.compute_summary()
        proposals = []

        if summary["mission_success_rate"] < 70.0:
            proposals.append(self._make_proposal("mission_strategy", "Mission success rate below 70%", "Increase mission decomposition depth and add fallback branches"))
        if summary["goal_completion_rate"] < 80.0:
            proposals.append(self._make_proposal("goal_execution", "Goal completion rate below 80%", "Implement stricter dependency validation and pre-flight resource checks"))
        if summary["avg_planning_depth"] > 5.0:
            proposals.append(self._make_proposal("planning_depth", "Average planning depth exceeds 5", "Flatten goal hierarchy and merge atomic sub-tasks"))
        if summary["avg_execution_latency"] > 10.0:
            proposals.append(self._make_proposal("execution_latency", "High average execution latency", "Parallelize independent branches and optimize critical path scheduling"))
        if summary["resource_utilization"] < 0.3:
            proposals.append(self._make_proposal("resource_optimization", "Low resource utilization", "Increase concurrency limits and batch low-cost tasks"))
        if summary["recovery_rate"] < 60.0:
            proposals.append(self._make_proposal("failure_recovery", "Recovery rate below 60%", "Enhance replanner with alternative path generation and state rollback"))
        if summary["avg_decision_confidence"] < 0.6:
            proposals.append(self._make_proposal("decision_confidence", "Low decision confidence", "Require additional consensus evaluators and memory context recall"))

        if graph:
            cycle_risk = graph.detect_cycle()
            if cycle_risk:
                proposals.append(self._make_proposal("graph_integrity", "Cyclic dependencies detected", "Enforce DAG validation before scheduling and break circular references"))

        logger.info("Meta analysis complete: %d proposals generated", len(proposals))
        return proposals

    def _make_proposal(self, target: str, reason: str, recommendation: str) -> Dict[str, Any]:
        return {"type": "improvement", "target": target, "reason": reason, "recommendation": recommendation, "priority": "high"}
