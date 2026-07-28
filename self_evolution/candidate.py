"""Candidate patch model and serialization."""
import os
import json
import time
import hashlib
from typing import Dict, Any, List
from .config import CANDIDATES_DIR

class CandidatePatch:
    def __init__(self, finding_type: str, reason: str, affected_files: List[str],
                 risk_level: str, estimated_gain: float, rollback_info: Dict[str, str],
                 proposed_changes: Dict[str, str]):
        self.id = f"cand_{int(time.time())}_{hashlib.md5(reason.encode()).hexdigest()[:8]}"
        self.finding_type = finding_type
        self.reason = reason
        self.affected_files = affected_files
        self.risk_level = risk_level
        self.estimated_gain = estimated_gain
        self.rollback_info = rollback_info
        self.proposed_changes = proposed_changes
        self.status = "pending"
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "finding_type": self.finding_type,
            "reason": self.reason,
            "affected_files": self.affected_files,
            "risk_level": self.risk_level,
            "estimated_gain": self.estimated_gain,
            "rollback_info": self.rollback_info,
            "proposed_changes": self.proposed_changes,
            "status": self.status,
            "created_at": self.created_at
        }

    def save(self) -> str:
        os.makedirs(CANDIDATES_DIR, exist_ok=True)
        path = os.path.join(CANDIDATES_DIR, f"{self.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return path
