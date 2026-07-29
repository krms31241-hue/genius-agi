"""Execution Monitor: Detects deadlocks, starvation, timeouts, stalls, resource exhaustion."""
import time
import logging
from typing import Dict, Any, List
from .executive_models import TaskState, GoalStatus, ExecutionMetrics
from .task_graph import TaskGraph

logger = logging.getLogger(__name__)

class ExecutionMonitor:
    def __init__(self, graph: TaskGraph, tracker_states: Dict[str, TaskState], timeout_sec: float = 300.0):
        self.graph = graph
        self.states = tracker_states
        self.timeout = timeout_sec

    def analyze(self) -> ExecutionMetrics:
        metrics = ExecutionMetrics(total_tasks=len(self.states))
        now = time.time()
        waiting_deps = {tid: [d for d in self.graph.nodes[tid].dependencies if self.states.get(d, TaskState(d)).status not in (GoalStatus.COMPLETED, GoalStatus.FAILED)]
                        for tid, st in self.states.items() if st.status == GoalStatus.WAITING}
        
        metrics.deadlock_detected = self._check_deadlock(waiting_deps)
        metrics.starvation_detected = self._check_starvation(now)
        metrics.timeout_detected = self._check_timeouts(now)
        stalled = self._check_stalled(now)
        metrics.resource_usage = sum(1 for s in self.states.values() if s.status == GoalStatus.RUNNING) / max(1, len(self.states))
        
        metrics.completed = sum(1 for s in self.states.values() if s.status == GoalStatus.COMPLETED)
        metrics.failed = sum(1 for s in self.states.values() if s.status == GoalStatus.FAILED)
        metrics.blocked = sum(1 for s in self.states.values() if s.status == GoalStatus.WAITING)
        metrics.running = sum(1 for s in self.states.values() if s.status == GoalStatus.RUNNING)
        
        if metrics.deadlock_detected or metrics.timeout_detected or stalled:
            logger.warning("Execution anomalies detected: deadlock=%s timeout=%s stalled=%s", metrics.deadlock_detected, metrics.timeout_detected, stalled)
        return metrics

    def _check_deadlock(self, waiting_deps: Dict[str, List[str]]) -> bool:
        visited = set()
        def dfs(node):
            if node in visited: return True
            visited.add(node)
            for dep in waiting_deps.get(node, []):
                if dfs(dep): return True
            visited.discard(node)
            return False
        return any(dfs(n) for n in waiting_deps)

    def _check_starvation(self, now: float) -> bool:
        waiting = [s for s in self.states.values() if s.status == GoalStatus.WAITING]
        return any((now - (s.started_at or s.completed_at or now)) > self.timeout * 2 for s in waiting)

    def _check_timeouts(self, now: float) -> bool:
        return any(s.status == GoalStatus.RUNNING and (now - (s.started_at or now)) > self.timeout for s in self.states.values())

    def _check_stalled(self, now: float) -> bool:
        running = [s for s in self.states.values() if s.status == GoalStatus.RUNNING]
        return all(s.progress_pct < 10.0 and (now - (s.started_at or now)) > self.timeout * 0.5 for s in running) if running else False
