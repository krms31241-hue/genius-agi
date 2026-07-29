"""Objective Model: Focused outcome container bridging campaigns and goals."""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

class ObjectiveStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Objective:
    id: str
    title: str
    description: str = ""
    status: ObjectiveStatus = ObjectiveStatus.DRAFT
    priority: float = 0.0
    goals: List[str] = field(default_factory=list)
    parent_campaign_id: str = ""
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        return d
