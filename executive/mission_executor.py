"""Mission Executor: End-to-end mission execution with pause/resume/cancel, recovery, and persistence."""
import os
import time
import json
import tempfile
import shutil
import logging
from typing import Dict, Any, List, Optional, Callable
from .mission import MissionManager, Mission, MissionStatus
from .goal import GoalManager
from .task_graph import TaskGraph
from .adaptive_scheduler import AdaptiveScheduler
from .resource_manager import ResourceManager
from .execution_context import ExecutionContext, ContextStatus
from .execution_history import ExecutionHistory, TaskExecutionRecord
from .recovery_manager import RecoveryManager, RecoveryStrategy

logger = logging.getLogger(__name__)

class MissionExecutor:
    def __init__(self, mission_mgr: MissionManager, goal_mgr: GoalManager,
                 resource_mgr: ResourceManager, data_dir: str = "executive_data",
                 task_runner: Optional[Callable[[str, Dict[str, Any]], bool]] = None):
        self.mission_mgr = mission_mgr
        self.goal_mgr = goal_mgr
        self.resource_mgr = resource_mgr
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.checkpoint_path = os.path.join(self.data_dir, "executor_checkpoint.json")

        self.history = ExecutionHistory(data_dir=data_dir)
        self.recovery = RecoveryManager(history=self.history)
        self.context: Optional[ExecutionContext] = None
        self.task_runner = task_runner or self._default_task_runner

    def _default_task_runner(self, task_id: str, ctx: Dict[str, Any]) -> bool:
        if "fail" in task_id.lower():
            raise RuntimeError(f"Simulated failure for task {task_id}")
        return True

    def execute_mission(self, mission: Mission, graph: TaskGraph, scheduler: AdaptiveScheduler) -> Dict[str, Any]:
        self.context = ExecutionContext(mission_id=mission.id)
        self.recovery.save_checkpoint(mission.id, self.context, {"graph_nodes": list(graph.nodes.keys())})
        self.mission_mgr.transition_status(mission, MissionStatus.ACTIVE)

        tasks = scheduler.schedule()
        results: Dict[str, Any] = {"completed": [], "failed": [], "skipped": [], "status": "running"}

        for task_id in tasks:
            if self.context.status == ContextStatus.CANCELLED:
                results["status"] = "cancelled"
                break
            while self.context.status == ContextStatus.PAUSED:
                time.sleep(0.05)

            self.context.push_task(task_id)
            success, error_msg = self._run_task(task_id, mission.id)
            self.context.pop_task()

            if success:
                results["completed"].append(task_id)
            else:
                results["failed"].append(task_id)
                strategy = self.recovery.execute_recovery(task_id, error_msg, self.context)
                if strategy == RecoveryStrategy.ROLLBACK:
                    if self.rollback(mission.id):
                        rollback_record = TaskExecutionRecord(
                            task_id=task_id, mission_id=mission.id,
                            status="rollback", result="rolled_back",
                            started_at=time.time(), completed_at=time.time()
                        )
                        self.history.record_task(rollback_record)
                        results["status"] = "rolled_back"
                    else:
                        results["status"] = "failed"
                    break
                elif strategy == RecoveryStrategy.SKIP:
                    results["skipped"].append(task_id)

        if results["status"] == "running" and not results["failed"]:
            results["status"] = "completed"
            self.mission_mgr.transition_status(mission, MissionStatus.COMPLETED)
        elif results["status"] == "running":
            results["status"] = "failed"
            self.mission_mgr.transition_status(mission, MissionStatus.FAILED)

        self._save_checkpoint()
        return results

    def _run_task(self, task_id: str, mission_id: str) -> tuple[bool, str]:
        record = TaskExecutionRecord(task_id=task_id, mission_id=mission_id, started_at=time.time())
        try:
            self.task_runner(task_id, self.context.shared_context if self.context else {})
            record.status = "success"
            record.result = "completed"
            record.completed_at = time.time()
            record.duration = record.completed_at - record.started_at
            self.history.record_task(record)
            return True, ""
        except Exception as e:
            record.status = "failed"
            record.error = str(e)
            record.completed_at = time.time()
            record.duration = record.completed_at - record.started_at
            record.retry_count += 1
            self.history.record_task(record)
            return False, str(e)

    def pause(self) -> None:
        if self.context:
            self.context.status = ContextStatus.PAUSED
            self.context.updated_at = time.time()
            self._save_checkpoint()
            logger.info("Mission %s paused", self.context.mission_id)

    def resume(self) -> None:
        if self.context and self.context.status == ContextStatus.PAUSED:
            self.context.status = ContextStatus.RUNNING
            self.context.updated_at = time.time()
            logger.info("Mission %s resumed", self.context.mission_id)

    def cancel(self) -> None:
        if self.context:
            self.context.status = ContextStatus.CANCELLED
            self.context.updated_at = time.time()
            self._save_checkpoint()
            logger.info("Mission %s cancelled", self.context.mission_id)

    def rollback(self, mission_id: str) -> bool:
        checkpoint = self.recovery.restore_checkpoint(mission_id)
        if checkpoint:
            self.context = ExecutionContext.from_dict(checkpoint["context"])
            logger.info("Rolled back mission %s to checkpoint", mission_id)
            return True
        return False

    def _save_checkpoint(self) -> None:
        if not self.context:
            return
        data = {"context": self.context.to_dict(), "timestamp": time.time()}
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, self.checkpoint_path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)

    def load_checkpoint(self) -> Optional[ExecutionContext]:
        try:
            with open(self.checkpoint_path, 'r') as f:
                data = json.load(f)
            self.context = ExecutionContext.from_dict(data["context"])
            return self.context
        except Exception:
            return None
