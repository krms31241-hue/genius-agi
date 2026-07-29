"""Core data models for Executive Intelligence."""
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional

class GoalStatus(str, Enum):
    NEW = "new"
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Goal:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    priority: float = 0.0
    importance: float = 0.5
    urgency: float = 0.5
    deadline: Optional[float] = None
    status: GoalStatus = GoalStatus.NEW
    origin: str = "system"
    parent_goal: Optional[str] = None
    child_goals: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        if "status" in data:
            data["status"] = GoalStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class PlanNode:
    id: str
    action: str
    dependencies: List[str] = field(default_factory=list)
    expected_result: str = ""
    risk: float = 0.0
    estimated_cost: float = 0.0
    branch_type: str = "sequential"  # sequential, parallel, conditional, recovery, fallback
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TaskState:
    node_id: str
    status: GoalStatus = GoalStatus.NEW
    retry_count: int = 0
    max_retries: int = 3
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: str = ""
    progress_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

@dataclass
class ExecutionMetrics:
    total_tasks: int = 0
    completed: int = 0
    failed: int = 0
    blocked: int = 0
    running: int = 0
    avg_duration: float = 0.0
    resource_usage: float = 0.0
    deadlock_detected: bool = False
    starvation_detected: bool = False
    timeout_detected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
