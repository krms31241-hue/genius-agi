"""Goal lifecycle and state management."""
import os
import time
import json
import tempfile
import shutil
import logging
from typing import Dict, Any, List
from .executive_models import Goal, GoalStatus

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    GoalStatus.NEW: [GoalStatus.PLANNED, GoalStatus.CANCELLED],
    GoalStatus.PLANNED: [GoalStatus.SCHEDULED, GoalStatus.CANCELLED],
    GoalStatus.SCHEDULED: [GoalStatus.RUNNING, GoalStatus.WAITING, GoalStatus.CANCELLED],
    GoalStatus.RUNNING: [GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.WAITING],
    GoalStatus.WAITING: [GoalStatus.RUNNING, GoalStatus.CANCELLED],
    GoalStatus.COMPLETED: [],
    GoalStatus.FAILED: [GoalStatus.PLANNED, GoalStatus.CANCELLED],
    GoalStatus.CANCELLED: []
}

class GoalManager:
    """Manages goal state transitions, validation, and persistence."""
    def __init__(self, data_dir: str = "executive_data"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.goals_path = os.path.join(self.data_dir, "goals.json")
        self.history_path = os.path.join(self.data_dir, "goal_history.json")
        self._init_files()

    def _init_files(self):
        for p in [self.goals_path, self.history_path]:
            if not os.path.exists(p):
                self._atomic_save(p, [])

    def _atomic_save(self, path: str, data: Any):
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)
            raise

    def _load_json(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, 'r') as f: return json.load(f)
        except Exception: return []

    def add_goal(self, goal: Goal) -> bool:
        data = self._load_json(self.goals_path)
        data.append(goal.to_dict())
        self._atomic_save(self.goals_path, data)
        self._record_history("created", goal)
        logger.info("Goal added: %s", goal.id)
        return True

    def update_goal(self, goal: Goal) -> bool:
        data = self._load_json(self.goals_path)
        for i, g in enumerate(data):
            if g["id"] == goal.id:
                goal.updated_at = time.time()
                data[i] = goal.to_dict()
                self._atomic_save(self.goals_path, data)
                self._record_history("updated", goal)
                return True
        return False

    def transition_status(self, goal: Goal, new_status: GoalStatus) -> bool:
        if new_status not in VALID_TRANSITIONS.get(goal.status, []):
            logger.warning("Invalid transition: %s -> %s for goal %s", goal.status.value, new_status.value, goal.id)
            return False
        goal.status = new_status
        goal.updated_at = time.time()
        return self.update_goal(goal)

    def get_goal(self, goal_id: str) -> Goal:
        data = self._load_json(self.goals_path)
        for g in data:
            if g["id"] == goal_id:
                return Goal.from_dict(g)
        return None

    def list_goals(self, status: GoalStatus = None) -> List[Goal]:
        data = self._load_json(self.goals_path)
        goals = [Goal.from_dict(g) for g in data]
        if status:
            goals = [g for g in goals if g.status == status]
        return goals

    def _record_history(self, action: str, goal: Goal):
        hist = self._load_json(self.history_path)
        hist.append({"action": action, "goal_id": goal.id, "status": goal.status.value, "timestamp": time.time()})
        self._atomic_save(self.history_path, hist)
