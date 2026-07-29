"""Strategic Planning Engine: Goal decomposition, multi-algorithm search, DAG construction, and branch pruning."""
import heapq
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class PlanningAction:
    """Atomic executable step with prerequisites, effects, and cost."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    prerequisites: Set[str] = field(default_factory=set)
    effects: Set[str] = field(default_factory=set)
    cost: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "cost": self.cost,
            "prerequisites": list(self.prerequisites), "effects": list(self.effects),
            "metadata": self.metadata
        }

@dataclass
class StrategicPlan:
    """DAG-based execution plan with topological ordering and cost tracking."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    actions: List[PlanningAction] = field(default_factory=list)
    dag: Dict[str, List[str]] = field(default_factory=dict)
    topological_order: List[str] = field(default_factory=list)
    total_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actions": [a.to_dict() for a in self.actions],
            "dag": self.dag,
            "topological_order": self.topological_order,
            "total_cost": self.total_cost,
            "metadata": self.metadata
        }

class StrategicPlanningEngine:
    """Production-grade strategic planner supporting A*, Beam Search, Greedy, and cost-based optimization.
    Outputs validated, pruned DAG execution plans."""
    
    def __init__(self, 
                 heuristic_fn: Optional[Callable[[frozenset, frozenset, List[PlanningAction]], float]] = None,
                 min_action_cost: float = 1.0) -> None:
        self.heuristic_fn = heuristic_fn or self._default_heuristic
        self.min_action_cost = min_action_cost

    def split_goal(self, goal: str, decomposition_rules: Dict[str, List[str]]) -> List[str]:
        """Recursively split high-level goals into atomic subgoals using provided rules."""
        if goal not in decomposition_rules:
            return [goal]
        subgoals = []
        for sub in decomposition_rules[goal]:
            subgoals.extend(self.split_goal(sub, decomposition_rules))
        return subgoals

    def plan(self, 
             initial_state: Set[str], 
             goal_conditions: Set[str], 
             actions: List[PlanningAction],
             algorithm: str = "astar",
             beam_width: int = 3,
             max_iterations: int = 1000) -> StrategicPlan:
        """Generate an optimized execution plan using the specified search algorithm."""
        initial = frozenset(initial_state)
        goals = frozenset(goal_conditions)
        action_map = {a.id: a for a in actions}
        
        if algorithm == "astar":
            path = self._search_astar(initial, goals, actions, max_iterations)
        elif algorithm == "greedy":
            path = self._search_greedy(initial, goals, actions, max_iterations)
        elif algorithm == "beam":
            path = self._search_beam(initial, goals, actions, beam_width, max_iterations)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'astar', 'greedy', or 'beam'.")
            
        if not path:
            logger.warning("No valid plan found for goals: %s", goals)
            return StrategicPlan(metadata={"status": "failed", "reason": "no_path_found"})
            
        plan_actions = [action_map[aid] for aid in path]
        dag, topo_order = self._build_dag(plan_actions, goals)
        pruned_actions, pruned_dag, pruned_order = self._prune_impossible(plan_actions, dag, topo_order, goals)
        
        total_cost = sum(a.cost for a in pruned_actions)
        logger.info("Plan generated: %s | Algorithm: %s | Cost: %.2f | Steps: %d", 
                    algorithm, algorithm, total_cost, len(pruned_actions))
                    
        return StrategicPlan(
            actions=pruned_actions,
            dag=pruned_dag,
            topological_order=pruned_order,
            total_cost=round(total_cost, 4),
            metadata={"algorithm": algorithm, "status": "success"}
        )

    def _search_astar(self, initial: frozenset, goals: frozenset, actions: List[PlanningAction], max_iter: int) -> List[str]:
        """A* search: f(n) = g(n) + h(n)"""
        open_set = [(self.heuristic_fn(initial, goals, actions), 0.0, initial, [])]
        visited: Dict[frozenset, float] = {}
        iterations = 0
        
        while open_set and iterations < max_iter:
            iterations += 1
            f, g, state, path = heapq.heappop(open_set)
            
            if goals.issubset(state):
                return path
            if state in visited and visited[state] <= g:
                continue
            visited[state] = g
            
            for action in actions:
                if action.prerequisites.issubset(state):
                    new_state = state | frozenset(action.effects)
                    new_g = g + action.cost
                    new_h = self.heuristic_fn(new_state, goals, actions)
                    new_f = new_g + new_h
                    if new_state not in visited or visited[new_state] > new_g:
                        heapq.heappush(open_set, (new_f, new_g, new_state, path + [action.id]))
        return []

    def _search_greedy(self, initial: frozenset, goals: frozenset, actions: List[PlanningAction], max_iter: int) -> List[str]:
        """Greedy best-first search: f(n) = h(n)"""
        open_set = [(self.heuristic_fn(initial, goals, actions), 0.0, initial, [])]
        visited: Set[frozenset] = set()
        iterations = 0
        
        while open_set and iterations < max_iter:
            iterations += 1
            h, g, state, path = heapq.heappop(open_set)
            
            if goals.issubset(state):
                return path
            if state in visited:
                continue
            visited.add(state)
            
            for action in actions:
                if action.prerequisites.issubset(state):
                    new_state = state | frozenset(action.effects)
                    if new_state not in visited:
                        new_g = g + action.cost
                        new_h = self.heuristic_fn(new_state, goals, actions)
                        heapq.heappush(open_set, (new_h, new_g, new_state, path + [action.id]))
        return []

    def _search_beam(self, initial: frozenset, goals: frozenset, actions: List[PlanningAction], beam_width: int, max_iter: int) -> List[str]:
        """Beam search: keeps top K nodes per level by f(n)"""
        current_level = [(self.heuristic_fn(initial, goals, actions), 0.0, initial, [])]
        visited: Set[frozenset] = set()
        iterations = 0
        
        while current_level and iterations < max_iter:
            iterations += 1
            next_level = []
            for h, g, state, path in current_level:
                if goals.issubset(state):
                    return path
                if state in visited:
                    continue
                visited.add(state)
                
                for action in actions:
                    if action.prerequisites.issubset(state):
                        new_state = state | frozenset(action.effects)
                        if new_state not in visited:
                            new_g = g + action.cost
                            new_h = self.heuristic_fn(new_state, goals, actions)
                            next_level.append((new_h + new_g, new_g, new_state, path + [action.id]))
                            
            next_level.sort(key=lambda x: (x[0], x[3]))
            current_level = next_level[:beam_width]
        return []

    def _build_dag(self, actions: List[PlanningAction], goals: frozenset) -> Tuple[Dict[str, List[str]], List[str]]:
        """Construct dependency DAG and compute topological order."""
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {a.id: 0 for a in actions}
        effect_producers: Dict[str, str] = {}
        
        for a in actions:
            for eff in a.effects:
                effect_producers[eff] = a.id
                
        for a in actions:
            for prereq in a.prerequisites:
                if prereq in effect_producers:
                    parent = effect_producers[prereq]
                    if a.id not in adj[parent]:
                        adj[parent].append(a.id)
                        in_degree[a.id] += 1
                        
        # Kahn's algorithm for topological sort
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        topo_order = []
        temp_in = dict(in_degree)
        
        while queue:
            node = queue.popleft()
            topo_order.append(node)
            for neighbor in adj.get(node, []):
                temp_in[neighbor] -= 1
                if temp_in[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(topo_order) != len(actions):
            logger.warning("Cycle detected in plan DAG. Returning partial order.")
            
        return dict(adj), topo_order

    def _prune_impossible(self, actions: List[PlanningAction], dag: Dict[str, List[str]], 
                          topo_order: List[str], goals: frozenset) -> Tuple[List[PlanningAction], Dict[str, List[str]], List[str]]:
        """Remove branches that do not contribute to achieving goal conditions."""
        action_map = {a.id: a for a in actions}
        relevant_ids: Set[str] = set()
        
        # Backward reachability from goals
        goal_producers = set()
        for a in actions:
            if a.effects & goals:
                goal_producers.add(a.id)
                
        queue = deque(goal_producers)
        while queue:
            nid = queue.popleft()
            if nid in relevant_ids:
                continue
            relevant_ids.add(nid)
            # Find parents in DAG
            for parent, children in dag.items():
                if nid in children and parent not in relevant_ids:
                    queue.append(parent)
                    
        # Filter actions and rebuild DAG
        pruned_actions = [a for a in actions if a.id in relevant_ids]
        pruned_dag = {k: [v for v in vs if v in relevant_ids] for k, vs in dag.items() if k in relevant_ids}
        pruned_order = [nid for nid in topo_order if nid in relevant_ids]
        
        return pruned_actions, pruned_dag, pruned_order

    def _default_heuristic(self, state: frozenset, goals: frozenset, actions: List[PlanningAction]) -> float:
        """Admissible heuristic: unmet goals * minimum action cost."""
        unmet = len(goals - state)
        return unmet * self.min_action_cost
