"""Dynamic Goal Manager: Safe runtime goal injection, priority recalculation, and dependency updates."""
import time
import hashlib
import logging
import threading
from typing import Dict, Any, List, Optional
from .goal import GoalManager
from .goal_priority import GoalPriorityEngine
from .task_graph import TaskGraph
from .scheduler import Scheduler
from .adaptive_scheduler import AdaptiveScheduler
from .executive_models import Goal, GoalStatus, PlanNode

logger = logging.getLogger(__name__)

class DynamicGoalManager:
    """Orchestrates safe injection of new goals during execution.
    Handles dependency validation, cycle prevention, priority recalculation, and scheduler updates."""
    
    def __init__(self, goal_mgr: GoalManager, prioritizer: GoalPriorityEngine,
                 graph: TaskGraph, scheduler: Scheduler, planner: Any = None):
        self.goal_mgr = goal_mgr
        self.prioritizer = prioritizer
        self.graph = graph
        self.scheduler = scheduler
        self.lock = threading.RLock()

    def inject_goal(self, goal: Goal, dependencies: List[str] = None, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Safely inject a new goal into the active execution pipeline."""
        with self.lock:
            context = context or {}
            deps = dependencies or goal.dependencies or []
            
            # 1. Validate & Persist Goal
            if not self.goal_mgr.validate_goal(goal):
                return {"success": False, "reason": "Invalid goal structure"}
            
            self.goal_mgr.add_goal(goal)
            goal.dependencies = deps
            self.goal_mgr.update_goal(goal)
                
            # 2. Create PlanNode directly to preserve explicit dependencies
            # Bypasses Planner.create_plan filtering which drops external graph references
            nid = hashlib.sha256(f"plan_{goal.id}".encode()).hexdigest()[:12]
            new_node = PlanNode(
                id=nid, action=goal.description or goal.title, dependencies=list(deps),
                expected_result=f"Completion of {goal.title}", risk=goal.metadata.get("risk", 0.3),
                estimated_cost=goal.metadata.get("resource_cost", 1.0), branch_type="sequential",
                metadata={"goal_id": goal.id}
            )
            new_nodes = [new_node]
                
            # 3. Update Dependency Graph Safely
            temp_nodes = dict(self.graph.nodes)
            temp_adj = {k: list(v) for k, v in self.graph.adj.items()}
            temp_in_degree = dict(self.graph.in_degree)
            
            for node in new_nodes:
                temp_nodes[node.id] = node
                temp_adj.setdefault(node.id, [])
                temp_in_degree.setdefault(node.id, 0)
                for dep in node.dependencies:
                    if dep in temp_nodes:
                        temp_adj.setdefault(dep, []).append(node.id)
                        temp_in_degree[node.id] = temp_in_degree.get(node.id, 0) + 1
                    else:
                        return {"success": False, "reason": f"Missing dependency: {dep}"}
                        
            # 4. Cycle Detection
            if self._detect_cycle_temp(temp_nodes, temp_adj):
                return {"success": False, "reason": "Injection would create dependency cycle"}
                
            # 5. Commit Graph Updates
            self.graph.nodes = temp_nodes
            self.graph.adj = temp_adj
            self.graph.in_degree = temp_in_degree
            
            # 6. Priority Recalculation
            all_goals = self.goal_mgr.list_goals()
            active_goals = [g for g in all_goals if g.status in (GoalStatus.NEW, GoalStatus.PLANNED, GoalStatus.SCHEDULED)]
            self.prioritizer.score_goals(active_goals)
            
            # Persist updated priorities so list_goals() reflects changes
            for g in active_goals:
                self.goal_mgr.update_goal(g)
                
            # 7. Update Scheduler
            new_priorities = {n.metadata.get("goal_id", n.id): g.priority 
                            for g in active_goals for n in new_nodes if n.metadata.get("goal_id") == g.id}
            if hasattr(self.scheduler, 'priorities'):
                self.scheduler.priorities.update(new_priorities)
                
            # 8. Trigger Reschedule if supported
            rescheduled = []
            if isinstance(self.scheduler, AdaptiveScheduler):
                rescheduled = self.scheduler.reschedule_waiting()
            elif hasattr(self.scheduler, 'schedule'):
                self.scheduler.schedule()
                
            logger.info("Goal %s injected successfully. New tasks scheduled: %d", goal.id, len(new_nodes))
            return {
                "success": True,
                "goal_id": goal.id,
                "tasks_added": [n.id for n in new_nodes],
                "rescheduled_tasks": rescheduled,
                "timestamp": time.time()
            }

    def _detect_cycle_temp(self, nodes: Dict[str, PlanNode], adj: Dict[str, List[str]]) -> bool:
        visited = set()
        rec_stack = set()
        def dfs(u):
            visited.add(u)
            rec_stack.add(u)
            for v in adj.get(u, []):
                if v not in visited:
                    if dfs(v): return True
                elif v in rec_stack: return True
            rec_stack.discard(u)
            return False
        return any(dfs(n) for n in nodes if n not in visited)
