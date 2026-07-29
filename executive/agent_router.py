"""Agent Router: Priority routing, dependency ordering, conflict prevention, and load balancing."""
import threading
import logging
from typing import Dict, Any, Set, Optional, List
from .agent_registry import AgentRegistry

logger = logging.getLogger(__name__)

class AgentRouter:
    """Deterministic task routing with dependency checks and conflict prevention."""
    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.lock = threading.RLock()
        self.exclusive_capabilities: Set[str] = set()
        self.busy_exclusive: Set[str] = set()
        self.active_routes: Dict[str, str] = {}  # task_id -> agent_id
        self.task_capabilities: Dict[str, str] = {}  # task_id -> capability

    def route_task(self, task_id: str, capability: str, priority: int = 0,
                   dependencies: List[str] = None, completed_tasks: Set[str] = None) -> Optional[str]:
        """Route task to best available agent. Returns agent_id or None if unavailable/blocked."""
        deps = dependencies or []
        completed = completed_tasks or set()

        # Dependency ordering check
        if not all(d in completed for d in deps):
            logger.debug("Task %s blocked by unmet dependencies", task_id)
            return None

        with self.lock:
            # Conflict prevention: exclusive capability routing
            if capability in self.exclusive_capabilities and capability in self.busy_exclusive:
                logger.debug("Capability %s exclusively locked. Deferring task %s", capability, task_id)
                return None

            agent_id = self.registry.get_available(capability)
            if not agent_id:
                logger.warning("No available agent for capability: %s", capability)
                return None

            self.active_routes[task_id] = agent_id
            self.task_capabilities[task_id] = capability
            self.registry.update_load(agent_id, 1)
            
            if capability in self.exclusive_capabilities:
                self.busy_exclusive.add(capability)
                
            logger.info("Routed task %s to agent %s (priority: %d)", task_id, agent_id, priority)
            return agent_id

    def release_route(self, task_id: str) -> None:
        with self.lock:
            agent_id = self.active_routes.pop(task_id, None)
            capability = self.task_capabilities.pop(task_id, None)
            if agent_id:
                self.registry.update_load(agent_id, -1)
            if capability and capability in self.exclusive_capabilities:
                self.busy_exclusive.discard(capability)

    def set_exclusive_capability(self, capability: str, exclusive: bool = True) -> None:
        with self.lock:
            if exclusive:
                self.exclusive_capabilities.add(capability)
            else:
                self.exclusive_capabilities.discard(capability)
