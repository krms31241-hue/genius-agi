"""Mission Manager: Long-term objective lifecycle and hierarchy."""
import os
import time
import json
import tempfile
import shutil
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class MissionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

VALID_MISSION_TRANSITIONS = {
    MissionStatus.DRAFT: [MissionStatus.ACTIVE, MissionStatus.CANCELLED],
    MissionStatus.ACTIVE: [MissionStatus.PAUSED, MissionStatus.COMPLETED, MissionStatus.FAILED, MissionStatus.CANCELLED],
    MissionStatus.PAUSED: [MissionStatus.ACTIVE, MissionStatus.CANCELLED],
    MissionStatus.COMPLETED: [],
    MissionStatus.CANCELLED: [],
    MissionStatus.FAILED: [MissionStatus.DRAFT, MissionStatus.CANCELLED]
}

@dataclass
class Mission:
    id: str
    title: str
    description: str = ""
    status: MissionStatus = MissionStatus.DRAFT
    objectives: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    parent_mission: Optional[str] = None
    child_missions: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        if "status" in data:
            data["status"] = MissionStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class MissionManager:
    """Manages mission lifecycle, hierarchy, persistence, and statistics."""
    def __init__(self, data_dir: str = "executive_data"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.missions_path = os.path.join(self.data_dir, "missions.json")
        self.history_path = os.path.join(self.data_dir, "mission_history.json")
        self._init_files()

    def _init_files(self):
        for p in [self.missions_path, self.history_path]:
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

    def create_mission(self, mission: Mission) -> bool:
        data = self._load_json(self.missions_path)
        data.append(mission.to_dict())
        self._atomic_save(self.missions_path, data)
        self._record_history("created", mission)
        logger.info("Mission created: %s", mission.id)
        return True

    def update_mission(self, mission: Mission) -> bool:
        data = self._load_json(self.missions_path)
        for i, m in enumerate(data):
            if m["id"] == mission.id:
                mission.updated_at = time.time()
                data[i] = mission.to_dict()
                self._atomic_save(self.missions_path, data)
                self._record_history("updated", mission)
                return True
        return False

    def transition_status(self, mission: Mission, new_status: MissionStatus) -> bool:
        if new_status not in VALID_MISSION_TRANSITIONS.get(mission.status, []):
            logger.warning("Invalid mission transition: %s -> %s", mission.status.value, new_status.value)
            return False
        mission.status = new_status
        mission.updated_at = time.time()
        return self.update_mission(mission)

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        data = self._load_json(self.missions_path)
        for m in data:
            if m["id"] == mission_id:
                return Mission.from_dict(m)
        return None

    def list_missions(self, status: MissionStatus = None) -> List[Mission]:
        data = self._load_json(self.missions_path)
        missions = [Mission.from_dict(m) for m in data]
        if status:
            missions = [m for m in missions if m.status == status]
        return missions

    def get_statistics(self) -> Dict[str, Any]:
        missions = self.list_missions()
        total = len(missions)
        if total == 0:
            return {"total": 0, "active": 0, "completed": 0, "failed": 0, "success_rate": 0.0}
        active = sum(1 for m in missions if m.status == MissionStatus.ACTIVE)
        completed = sum(1 for m in missions if m.status == MissionStatus.COMPLETED)
        failed = sum(1 for m in missions if m.status == MissionStatus.FAILED)
        success_rate = (completed / max(1, completed + failed)) * 100.0
        return {"total": total, "active": active, "completed": completed, "failed": failed, "success_rate": round(success_rate, 2)}

    def _record_history(self, action: str, mission: Mission):
        hist = self._load_json(self.history_path)
        hist.append({"action": action, "mission_id": mission.id, "status": mission.status.value, "timestamp": time.time()})
        self._atomic_save(self.history_path, hist)
