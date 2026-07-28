"""Policy Data Model."""
import time
import uuid
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

@dataclass
class Policy:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    author: str = "system"
    score: float = 0.0
    status: str = "draft"  # draft, active, disabled, archived
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
