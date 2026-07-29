"""Recovery Manager: Failure classification, strategy selection, checkpoint restore, and rollback."""
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional
from .execution_context import ExecutionContext
from .execution_history import ExecutionHistory

logger = logging.getLogger(__name__)

class FailureType(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    RESOURCE = "resource"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"

class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    ROLLBACK = "rollback"
    SKIP = "skip"
    ESCALATE = "escalate"

class RecoveryManager:
    def __init__(self, history: ExecutionHistory, max_retries: int = 3):
        self.history = history
        self.max_retries = max_retries
        self.checkpoints: Dict[str, Dict[str, Any]] = {}

    def classify_failure(self, error: str) -> FailureType:
        err_lower = error.lower()
        if "timeout" in err_lower or "time limit" in err_lower:
            return FailureType.TIMEOUT
        if "resource" in err_lower or "memory" in err_lower or "disk" in err_lower:
            return FailureType.RESOURCE
        if "transient" in err_lower or "network" in err_lower or "temporary" in err_lower:
            return FailureType.TRANSIENT
        if "permanent" in err_lower or "invalid" in err_lower or "syntax" in err_lower:
            return FailureType.PERMANENT
        return FailureType.UNKNOWN

    def get_strategy(self, failure_type: FailureType, task_id: str) -> RecoveryStrategy:
        stats = self.history.get_task_stats(task_id)
        if stats["total_retries"] >= self.max_retries:
            return RecoveryStrategy.ESCALATE
        if failure_type in (FailureType.TRANSIENT, FailureType.TIMEOUT, FailureType.RESOURCE):
            return RecoveryStrategy.RETRY
        if failure_type == FailureType.PERMANENT:
            return RecoveryStrategy.ROLLBACK
        return RecoveryStrategy.RETRY

    def save_checkpoint(self, mission_id: str, context: ExecutionContext, state: Dict[str, Any]) -> None:
        self.checkpoints[mission_id] = {
            "context": context.to_dict(),
            "state": state,
            "timestamp": time.time()
        }
        logger.info("Checkpoint saved for mission %s", mission_id)

    def restore_checkpoint(self, mission_id: str) -> Optional[Dict[str, Any]]:
        return self.checkpoints.get(mission_id)

    def execute_recovery(self, task_id: str, error: str, context: ExecutionContext) -> RecoveryStrategy:
        f_type = self.classify_failure(error)
        strategy = self.get_strategy(f_type, task_id)
        logger.info("Recovery strategy for %s: %s (failure: %s)", task_id, strategy.value, f_type.value)
        return strategy
