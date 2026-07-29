"""Loop State: Tracks autonomous executive loop phase, iteration, metrics, and control flags."""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

class LoopPhase(str, Enum):
    OBSERVE = "observe"
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    IMPROVE = "improve"

class LoopStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
    COMPLETED = "completed"

@dataclass
class LoopState:
    """Deterministic state container for the autonomous executive loop."""
    iteration: int = 0
    phase: LoopPhase = LoopPhase.OBSERVE
    status: LoopStatus = LoopStatus.IDLE
    stop_requested: bool = False
    consecutive_failures: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_recoveries: int = 0
    phase_durations: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    started_at: float = 0.0
    updated_at: float = field(default_factory=time.monotonic)

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["phase"] = self.phase.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoopState":
        if "phase" in data:
            data["phase"] = LoopPhase(data["phase"])
        if "status" in data:
            data["status"] = LoopStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
