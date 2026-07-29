"""Adaptive Scheduler: Dynamic queue, priority boosting, deadline/resource awareness, auto-rescheduling."""
import time
import logging
from typing import List, Dict, Any, Set
from .task_graph import TaskGraph
from .resource_manager import ResourceManager
from .executive_models import PlanNode

logger = logging.getLogger(__name__)

class AdaptiveScheduler:
    """Extends scheduling capabilities with dynamic adaptation and resource awareness."""
    def __init__(self, graph: TaskGraph, resource_mgr: ResourceManager, priorities: Dict[str, float] = None):
        self.graph = graph
        self.resources = resource_mgr
        self.priorities = priorities or {}
        self.scheduled: List[str] = []
        self.blocked: Set[str] = set()
        self.waiting: Set[str] = set()
        self.failed: Set[str] = set()
        self.age_boost: Dict[str, float] = {}

    def schedule(self) -> List[str]:
        order = self.graph.topological_sort()
        ready = []
        ready_ids = set()
        scheduled_set = set(self.scheduled)
        now = time.time()

        for nid in order:
            if nid in scheduled_set or nid in ready_ids:
                continue
            node = self.graph.nodes[nid]
            # Dependencies can be in past scheduled set OR current ready batch
            deps_met = all(d in scheduled_set or d in ready_ids or d not in self.graph.nodes for d in node.dependencies)
            if not deps_met:
                self.blocked.add(nid)
                continue

            # Priority boosting based on age
            age = now - node.metadata.get("created_at", now)
            boost = min(20.0, age / 60.0)
            self.age_boost[nid] = boost
            eff_priority = self.priorities.get(nid, 50.0) + boost

            # Resource check
            cost = {"cpu": node.estimated_cost * 0.2, "memory": node.estimated_cost * 0.3, "execution": 1.0, "time": node.estimated_cost}
            if not self.resources.allocate(nid, cost):
                self.waiting.add(nid)
                continue

            ready.append((nid, eff_priority))
            ready_ids.add(nid)

        ready.sort(key=lambda x: x[1], reverse=True)
        new_tasks = [r[0] for r in ready]
        self.scheduled.extend(new_tasks)
        logger.info("Adaptive schedule: %d ready, %d blocked, %d waiting", len(new_tasks), len(self.blocked), len(self.waiting))
        return self.scheduled

    def handle_failure(self, task_id: str):
        self.failed.add(task_id)
        self.resources.release(task_id)
        self.scheduled = [t for t in self.scheduled if t != task_id]
        self.blocked.discard(task_id)
        logger.info("Handled failure for %s, released resources", task_id)

    def reschedule_waiting(self):
        """Retry waiting tasks if resources freed up."""
        retry = []
        for nid in list(self.waiting):
            node = self.graph.nodes.get(nid)
            if not node: continue
            cost = {"cpu": node.estimated_cost * 0.2, "memory": node.estimated_cost * 0.3, "execution": 1.0, "time": node.estimated_cost}
            if self.resources.allocate(nid, cost):
                retry.append(nid)
                self.waiting.discard(nid)
        self.scheduled.extend(retry)
        return retry
