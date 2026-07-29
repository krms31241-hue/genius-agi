"""Executive Analytics: Tracks mission success, goal completion, latency, efficiency, utilization."""
import os
import time
import json
import tempfile
import shutil
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ExecutiveMetrics:
    """Persistent analytics engine for executive performance."""
    def __init__(self, data_dir: str = "executive_data"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.metrics_path = os.path.join(self.data_dir, "exec_metrics.json")
        self._init_state()

    def _init_state(self):
        if not os.path.exists(self.metrics_path):
            self._save({
                "missions_total": 0, "missions_completed": 0, "missions_failed": 0,
                "goals_total": 0, "goals_completed": 0, "goals_failed": 0,
                "planning_depth_sum": 0, "planning_count": 0,
                "latency_sum": 0.0, "latency_count": 0,
                "recovery_attempts": 0, "recovery_success": 0,
                "decision_confidence_sum": 0.0, "decision_count": 0,
                "resource_utilization_sum": 0.0, "resource_samples": 0,
                "events": []
            })

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.metrics_path, 'r') as f: return json.load(f)
        except Exception: return {}

    def _save(self, data: Dict[str, Any]):
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f: json.dump(data, f, indent=2)
            shutil.move(tmp, self.metrics_path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)

    def record_event(self, event_type: str, data: Dict[str, Any]):
        state = self._load()
        state["events"].append({"type": event_type, "data": data, "timestamp": time.time()})
        if len(state["events"]) > 1000:
            state["events"] = state["events"][-500:]
        self._save(state)

    def update_mission(self, completed: int = 0, failed: int = 0):
        state = self._load()
        state["missions_total"] += completed + failed
        state["missions_completed"] += completed
        state["missions_failed"] += failed
        self._save(state)

    def update_goal(self, completed: int = 0, failed: int = 0):
        state = self._load()
        state["goals_total"] += completed + failed
        state["goals_completed"] += completed
        state["goals_failed"] += failed
        self._save(state)

    def record_planning(self, depth: int):
        state = self._load()
        state["planning_depth_sum"] += depth
        state["planning_count"] += 1
        self._save(state)

    def record_latency(self, seconds: float):
        state = self._load()
        state["latency_sum"] += seconds
        state["latency_count"] += 1
        self._save(state)

    def record_recovery(self, success: bool):
        state = self._load()
        state["recovery_attempts"] += 1
        if success: state["recovery_success"] += 1
        self._save(state)

    def record_decision_confidence(self, confidence: float):
        state = self._load()
        state["decision_confidence_sum"] += confidence
        state["decision_count"] += 1
        self._save(state)

    def record_resource_utilization(self, utilization: float):
        state = self._load()
        state["resource_utilization_sum"] += utilization
        state["resource_samples"] += 1
        self._save(state)

    def compute_summary(self) -> Dict[str, Any]:
        s = self._load()
        m_total = max(1, s["missions_completed"] + s["missions_failed"])
        g_total = max(1, s["goals_completed"] + s["goals_failed"])
        return {
            "mission_success_rate": round((s["missions_completed"] / m_total) * 100, 2),
            "goal_completion_rate": round((s["goals_completed"] / g_total) * 100, 2),
            "avg_planning_depth": round(s["planning_depth_sum"] / max(1, s["planning_count"]), 2),
            "avg_execution_latency": round(s["latency_sum"] / max(1, s["latency_count"]), 3),
            "planning_efficiency": round(s["planning_count"] / max(1, s["goals_total"]), 3),
            "resource_utilization": round(s["resource_utilization_sum"] / max(1, s["resource_samples"]), 3),
            "recovery_rate": round((s["recovery_success"] / max(1, s["recovery_attempts"])) * 100, 2),
            "failure_rate": round((s["goals_failed"] / max(1, s["goals_total"])) * 100, 2),
            "avg_decision_confidence": round(s["decision_confidence_sum"] / max(1, s["decision_count"]), 3)
        }
