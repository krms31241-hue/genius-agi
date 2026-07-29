"""Execution Context: Maintains mission state, task stack, and shared metadata."""
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

class ContextStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

@dataclass
class ExecutionContext:
    mission_id: str
    current_goal_id: Optional[str] = None
    current_task_id: Optional[str] = None
    execution_stack: List[str] = field(default_factory=list)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ContextStatus = ContextStatus.RUNNING
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def push_task(self, task_id: str) -> None:
        self.execution_stack.append(task_id)
        self.current_task_id = task_id
        self.updated_at = time.time()

    def pop_task(self) -> Optional[str]:
        if self.execution_stack:
            task = self.execution_stack.pop()
            self.current_task_id = self.execution_stack[-1] if self.execution_stack else None
            self.updated_at = time.time()
            return task
        return None

    def to_dict(self) -> Dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        if "status" in data:
            data["status"] = ContextStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
