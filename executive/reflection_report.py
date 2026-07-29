"""Reflection Report: Structured container for post-execution analysis."""
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass
class ReflectionReport:
    """Deterministic report capturing execution outcomes, lessons, and improvement proposals."""
    execution_id: str
    timestamp: float = field(default_factory=time.time)
    success_rate: float = 0.0
    failure_count: int = 0
    efficiency_score: float = 0.0
    mistakes: List[str] = field(default_factory=list)
    lessons: List[str] = field(default_factory=list)
    improvement_proposals: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReflectionReport":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
