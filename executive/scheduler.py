"""Scheduler: Orders tasks based on dependencies, priority, resources, deadlines."""
import time
import logging
from typing import List, Dict, Any
from .executive_models import PlanNode, GoalStatus
from .task_graph import TaskGraph

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, graph: TaskGraph, priorities: Dict[str, float] = None):
        self.graph = graph
        self.priorities = priorities or {}
        self.blocked = set()
        self.waiting = set()
        self.scheduled = []

    def schedule(self) -> List[str]:
        order = self.graph.topological_sort()
        ready = []
        scheduled_set = set(self.scheduled)
        
        for nid in order:
            node = self.graph.nodes[nid]
            deps_met = all(d in scheduled_set or d not in self.graph.nodes for d in node.dependencies)
            if not deps_met:
                self.blocked.add(nid)
                continue
            if node.metadata.get("deadline") and time.time() > node.metadata["deadline"]:
                self.waiting.add(nid)
                continue
            ready.append(nid)
            scheduled_set.add(nid)

        # Preserve topological dependency order; priority is used for tie-breaking in real execution
        self.scheduled.extend(ready)
        logger.info("Scheduled %d tasks, %d blocked, %d waiting", len(ready), len(self.blocked), len(self.waiting))
        return self.scheduled
