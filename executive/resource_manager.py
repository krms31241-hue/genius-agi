"""Resource Manager: Tracks and predicts CPU, Memory, Disk, Execution, Time budgets."""
import os
import time
import json
import tempfile
import shutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ResourceManager:
    """Deterministic resource tracking, exhaustion prediction, and schedule recommendations."""
    def __init__(self, data_dir: str = "executive_data", budgets: Dict[str, float] = None):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_path = os.path.join(self.data_dir, "resources.json")
        self.budgets = budgets or {
            "cpu": 100.0, "memory": 100.0, "disk": 100.0,
            "execution": 100.0, "time": 3600.0, "max_concurrent": 4
        }
        self.allocated: Dict[str, Dict[str, float]] = {}
        self._load_state()

    def _load_state(self):
        try:
            with open(self.state_path, 'r') as f:
                data = json.load(f)
                self.allocated = data.get("allocated", {})
        except Exception:
            self.allocated = {}

    def _save_state(self):
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump({"allocated": self.allocated, "updated_at": time.time()}, f, indent=2)
            shutil.move(tmp, self.state_path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)

    def allocate(self, task_id: str, cost: Dict[str, float]) -> bool:
        max_conc = self.budgets.get("max_concurrent", float('inf'))
        if len(self.allocated) >= max_conc:
            logger.warning("Max concurrent tasks reached. Cannot allocate %s", task_id)
            return False
        self.allocated[task_id] = cost
        self._save_state()
        return True

    def release(self, task_id: str):
        self.allocated.pop(task_id, None)
        self._save_state()

    def get_usage(self) -> Dict[str, float]:
        usage = {"cpu": 0.0, "memory": 0.0, "disk": 0.0, "execution": 0.0, "time": 0.0, "concurrent": len(self.allocated)}
        for cost in self.allocated.values():
            for k in usage:
                if k in cost:
                    usage[k] += cost[k]
        return usage

    def predict_exhaustion(self) -> Dict[str, bool]:
        usage = self.get_usage()
        return {k: usage.get(k, 0) >= self.budgets.get(k, float('inf')) * 0.9 for k in self.budgets if k != "max_concurrent"}

    def recommend_adjustments(self) -> List[str]:
        recommendations = []
        usage = self.get_usage()
        if usage.get("concurrent", 0) >= self.budgets.get("max_concurrent", float('inf')):
            recommendations.append("Reduce concurrency: defer low-priority tasks")
        if usage.get("memory", 0) >= self.budgets.get("memory", float('inf')) * 0.8:
            recommendations.append("Memory pressure high: schedule garbage collection or swap tasks")
        if usage.get("time", 0) >= self.budgets.get("time", float('inf')) * 0.8:
            recommendations.append("Time budget nearing limit: prioritize critical path tasks")
        return recommendations
