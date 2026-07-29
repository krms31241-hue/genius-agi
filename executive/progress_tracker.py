"""Progress Tracker: Monitors completion, failures, retries, and execution percentage."""
import time
import logging
from typing import Dict, Any
from .executive_models import TaskState, GoalStatus, ExecutionMetrics

logger = logging.getLogger(__name__)

class ProgressTracker:
    def __init__(self):
        self.states: Dict[str, TaskState] = {}
        self.metrics = ExecutionMetrics()

    def init_tasks(self, task_ids: list):
        for tid in task_ids:
            self.states[tid] = TaskState(node_id=tid)
        self.metrics.total_tasks = len(task_ids)

    def update(self, task_id: str, status: GoalStatus, progress: float = 0.0, error: str = ""):
        if task_id not in self.states: return
        st = self.states[task_id]
        st.status = status
        st.progress_pct = progress
        if status == GoalStatus.RUNNING and not st.started_at:
            st.started_at = time.time()
        elif status in (GoalStatus.COMPLETED, GoalStatus.FAILED):
            st.completed_at = time.time()
        if error:
            st.error_message = error
            st.retry_count += 1
        self._recalc_metrics()

    def _recalc_metrics(self):
        self.metrics.completed = sum(1 for s in self.states.values() if s.status == GoalStatus.COMPLETED)
        self.metrics.failed = sum(1 for s in self.states.values() if s.status == GoalStatus.FAILED)
        self.metrics.running = sum(1 for s in self.states.values() if s.status == GoalStatus.RUNNING)
        self.metrics.blocked = sum(1 for s in self.states.values() if s.status == GoalStatus.WAITING)
        completed = [s for s in self.states.values() if s.completed_at and s.started_at]
        self.metrics.avg_duration = sum(s.completed_at - s.started_at for s in completed) / max(1, len(completed))

    def get_progress(self) -> Dict[str, Any]:
        total = max(1, self.metrics.total_tasks)
        pct = ((self.metrics.completed + self.metrics.failed) / total) * 100.0
        return {"total": total, "completed": self.metrics.completed, "failed": self.metrics.failed,
                "running": self.metrics.running, "blocked": self.metrics.blocked, "percentage": round(pct, 2)}
