"""Automatic crash recovery and state persistence."""
import os
import json
import time
from typing import Dict, Any, Optional

class CrashRecovery:
    def __init__(self, state_path: str = ".upgrade_state.json"):
        self.state_path = state_path
        self.state = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"stage": "idle", "snap_id": None, "timestamp": time.time(), "error": None}

    def save(self, stage: str, snap_id: Optional[str] = None, error: Optional[str] = None):
        self.state = {"stage": stage, "snap_id": snap_id, "timestamp": time.time(), "error": error}
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)

    def is_interrupted(self) -> bool:
        return self.state["stage"] not in ("idle", "completed", "rejected")

    def get_recovery_action(self) -> Dict[str, Any]:
        if not self.is_interrupted():
            return {"action": "none"}
        return {"action": "rollback", "snap_id": self.state.get("snap_id"), "failed_stage": self.state["stage"]}

    def clear(self):
        self.save("idle")
        # Do NOT remove the file here. File lifecycle ownership belongs to the caller/test.
