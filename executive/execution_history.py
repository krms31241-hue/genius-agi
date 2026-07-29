"""Execution History: Persistent record of task executions, durations, errors, and recoveries."""
import os
import json
import time
import tempfile
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class TaskExecutionRecord:
    task_id: str
    mission_id: str
    goal_id: Optional[str] = None
    started_at: float = 0.0
    completed_at: float = 0.0
    duration: float = 0.0
    status: str = "pending"
    result: str = ""
    error: str = ""
    retry_count: int = 0
    recovery_events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class ExecutionHistory:
    def __init__(self, data_dir: str = "executive_data"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.history_path = os.path.join(self.data_dir, "execution_history.json")
        self._init_file()

    def _init_file(self) -> None:
        if not os.path.exists(self.history_path):
            self._atomic_save([])

    def _atomic_save(self, data: Any) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, self.history_path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _load(self) -> List[Dict[str, Any]]:
        try:
            with open(self.history_path, 'r') as f:
                return json.load(f)
        except Exception:
            return []

    def record_task(self, record: TaskExecutionRecord) -> None:
        data = self._load()
        data.append(record.to_dict())
        self._atomic_save(data)
        logger.info("Recorded task execution: %s [%s]", record.task_id, record.status)

    def get_history(self, mission_id: Optional[str] = None) -> List[TaskExecutionRecord]:
        data = self._load()
        records = [TaskExecutionRecord(**r) for r in data]
        if mission_id:
            records = [r for r in records if r.mission_id == mission_id]
        return records

    def get_task_stats(self, task_id: str) -> Dict[str, Any]:
        records = [r for r in self.get_history() if r.task_id == task_id]
        if not records:
            return {"executions": 0, "successes": 0, "failures": 0, "total_retries": 0}
        return {
            "executions": len(records),
            "successes": sum(1 for r in records if r.status == "success"),
            "failures": sum(1 for r in records if r.status == "failed"),
            "total_retries": sum(r.retry_count for r in records)
        }
