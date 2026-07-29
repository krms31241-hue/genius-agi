"""Multi-Agent Coordinator: Orchestrates sequential/parallel execution, routing, timeouts, and recovery."""
import time
import threading
import logging
import concurrent.futures
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field
from .agent_registry import AgentRegistry, AgentInfo, AgentStatus
from .agent_session import SessionManager, SessionStatus
from .agent_router import AgentRouter

logger = logging.getLogger(__name__)

@dataclass
class AgentTask:
    id: str
    capability: str
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    dependencies: List[str] = field(default_factory=list)
    timeout_sec: float = 10.0
    max_retries: int = 1

class AgentCoordinator:
    """Coordinates multiple agents with routing, isolation, timeouts, and recovery."""
    def __init__(self, heartbeat_timeout: float = 30.0, default_timeout: float = 10.0, max_workers: int = 4):
        self.registry = AgentRegistry(heartbeat_timeout=heartbeat_timeout)
        self.sessions = SessionManager()
        self.router = AgentRouter(self.registry)
        self.default_timeout = default_timeout
        self.max_workers = max_workers
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.lock = threading.RLock()
        self.completed_tasks: Set[str] = set()
        self.results: Dict[str, Any] = {}
        self.errors: Dict[str, str] = {}

    def register_agent(self, agent_id: str, name: str, capabilities: List[str], max_concurrent: int = 3) -> bool:
        info = AgentInfo(id=agent_id, name=name, capabilities=capabilities, max_concurrent=max_concurrent)
        return self.registry.register(info)

    def deregister_agent(self, agent_id: str) -> bool:
        return self.registry.deregister(agent_id)

    def restart_agent(self, agent_id: str) -> bool:
        agent = self.registry.get_agent(agent_id)
        if not agent:
            return False
        self.registry.mark_offline(agent_id)
        agent.status = AgentStatus.RESTARTING
        agent.current_load = 0
        agent.last_heartbeat = time.monotonic()
        time.sleep(0.05)
        agent.status = AgentStatus.ACTIVE
        logger.info("Agent %s restarted successfully", agent_id)
        return True

    def execute_sequential(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Execute tasks sequentially with dependency ordering and failure isolation."""
        pending = list(tasks)
        max_iterations = len(pending) * 3
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1
            progress = False
            next_pending = []

            for task in pending:
                if task.id in self.completed_tasks:
                    progress = True
                    continue

                agent_id = self.router.route_task(
                    task.id, task.capability, task.priority,
                    task.dependencies, self.completed_tasks
                )

                if not agent_id:
                    next_pending.append(task)
                    continue

                success = self._run_task(task, agent_id)
                self.router.release_route(task.id)

                if success:
                    self.completed_tasks.add(task.id)
                    progress = True
                else:
                    next_pending.append(task)

            pending = next_pending
            if not progress and pending:
                logger.warning("Deadlock or unresolvable dependencies detected. Remaining: %d", len(pending))
                break

        return {"completed": list(self.completed_tasks), "failed": list(self.errors.keys()), "results": self.results}

    def execute_parallel(self, tasks: List[AgentTask]) -> Dict[str, Any]:
        """Execute tasks in parallel batches respecting dependencies and per-task timeouts."""
        pending = {t.id: t for t in tasks}
        completed = []
        failed = []
        task_statuses: Dict[str, str] = {}
        task_results: Dict[str, Any] = {}
        task_errors: Dict[str, str] = {}
        
        max_iterations = len(pending) * 3 + 1
        iteration = 0

        while pending and iteration < max_iterations:
            iteration += 1
            ready = []
            deferred = {}

            for tid, task in pending.items():
                if all(d in completed for d in task.dependencies):
                    ready.append(task)
                else:
                    deferred[tid] = task

            if not ready:
                break

            futures_map = {}
            start_times = {}
            for task in ready:
                agent_id = self.router.route_task(
                    task.id, task.capability, task.priority,
                    task.dependencies, set(completed)
                )
                if agent_id:
                    future = self.executor.submit(self._run_task, task, agent_id)
                    futures_map[future] = task
                    start_times[future] = time.monotonic()
                else:
                    deferred[task.id] = task

            # Process futures with explicit per-task timeout polling
            while futures_map:
                concurrent.futures.wait(futures_map.keys(), timeout=0.1, return_when=concurrent.futures.FIRST_COMPLETED)
                now = time.monotonic()
                
                for future in list(futures_map.keys()):
                    task = futures_map[future]
                    elapsed = now - start_times[future]
                    
                    if future.done():
                        futures_map.pop(future)
                        self.router.release_route(task.id)
                        try:
                            success = future.result()
                            if success:
                                completed.append(task.id)
                                task_statuses[task.id] = "completed"
                                task_results[task.id] = self.results.get(task.id)
                            else:
                                failed.append(task.id)
                                task_statuses[task.id] = "failed"
                                task_errors[task.id] = self.errors.get(task.id, "Execution failed")
                        except Exception as e:
                            failed.append(task.id)
                            task_statuses[task.id] = "failed"
                            task_errors[task.id] = str(e)
                    elif elapsed > task.timeout_sec:
                        futures_map.pop(future)
                        future.cancel()
                        self.router.release_route(task.id)
                        failed.append(task.id)
                        task_statuses[task.id] = "timeout"
                        task_errors[task.id] = "Timeout"
                        session = self.sessions.get_by_task(task.id)
                        if session:
                            self.sessions.timeout(session.session_id)

            pending = deferred

        self.completed_tasks.update(completed)
        self.errors.update(task_errors)
        self.results.update(task_results)

        return {
            "completed": completed,
            "failed": failed,
            "status": task_statuses,
            "errors": task_errors,
            "results": task_results
        }

    def _run_task(self, task: AgentTask, agent_id: str) -> bool:
        """Isolated task execution with session tracking, retries, and failure containment."""
        session = self.sessions.create(agent_id, task.id, {"priority": task.priority})
        self.sessions.start(session.session_id)
        self.registry.update_heartbeat(agent_id)

        attempt = 0
        while attempt <= task.max_retries:
            attempt += 1
            try:
                result = self._simulate_agent_execution(task, agent_id)
                self.sessions.complete(session.session_id, result)
                with self.lock:
                    self.results[task.id] = result
                return True
            except Exception as e:
                logger.warning("Task %s attempt %d failed: %s", task.id, attempt, e)
                if attempt > task.max_retries:
                    self.sessions.fail(session.session_id, str(e))
                    with self.lock:
                        self.errors[task.id] = str(e)
                    return False
                time.sleep(0.05 * attempt)
        return False

    def _simulate_agent_execution(self, task: AgentTask, agent_id: str) -> Any:
        """Deterministic simulation hook. Override or replace with real agent IPC in production."""
        if task.payload.get("simulate_failure"):
            raise RuntimeError(f"Simulated failure for {task.id}")
        if task.payload.get("simulate_timeout"):
            time.sleep(task.timeout_sec + 5.0)
        return {"agent": agent_id, "task": task.id, "status": "success", "data": task.payload.get("data")}

    def get_status(self) -> Dict[str, Any]:
        return {
            "agents": len(self.registry.list_agents()),
            "active_sessions": len(self.sessions.get_active()),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.errors),
            "timestamp": time.monotonic()
        }

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)
        logger.info("AgentCoordinator shutdown complete")
