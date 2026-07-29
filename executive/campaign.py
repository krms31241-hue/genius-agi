"""Campaign Model: Mid-term execution container bridging missions and objectives."""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Campaign:
    id: str
    title: str
    description: str = ""
    status: CampaignStatus = CampaignStatus.DRAFT
    objectives: List[str] = field(default_factory=list)
    parent_mission_id: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        return d
