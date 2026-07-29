"""Task Graph: DAG management, cycle detection, topological sort, critical path."""
import logging
from typing import List, Dict, Any, Set, Tuple
from collections import deque
from .executive_models import PlanNode

logger = logging.getLogger(__name__)

class TaskGraph:
    def __init__(self):
        self.nodes: Dict[str, PlanNode] = {}
        self.adj: Dict[str, List[str]] = {}
        self.in_degree: Dict[str, int] = {}

    def add_node(self, node: PlanNode):
        self.nodes[node.id] = node
        if node.id not in self.adj:
            self.adj[node.id] = []
        if node.id not in self.in_degree:
            self.in_degree[node.id] = 0
            
        for dep in node.dependencies:
            if dep not in self.adj:
                self.adj[dep] = []
            self.adj[dep].append(node.id)
            self.in_degree[node.id] = self.in_degree.get(node.id, 0) + 1

    def validate_deps(self) -> bool:
        for nid, node in self.nodes.items():
            for dep in node.dependencies:
                if dep not in self.nodes:
                    logger.warning("Missing dependency: %s -> %s", nid, dep)
                    return False
        return True

    def detect_cycle(self) -> bool:
        visited = set()
        rec_stack = set()
        def dfs(u):
            visited.add(u)
            rec_stack.add(u)
            for v in self.adj.get(u, []):
                if v not in visited:
                    if dfs(v): return True
                elif v in rec_stack: return True
            rec_stack.discard(u)
            return False
        for n in self.nodes:
            if n not in visited:
                if dfs(n): return True
        return False

    def topological_sort(self) -> List[str]:
        if self.detect_cycle():
            raise ValueError("Graph contains cycle, cannot sort")
        in_deg = dict(self.in_degree)
        q = deque([n for n in self.nodes if in_deg.get(n, 0) == 0])
        order = []
        while q:
            u = q.popleft()
            order.append(u)
            for v in self.adj.get(u, []):
                in_deg[v] -= 1
                if in_deg[v] == 0:
                    q.append(v)
        return order

    def critical_path(self) -> Tuple[List[str], float]:
        order = self.topological_sort()
        if not order: return [], 0.0
        
        dist = {n: -float('inf') for n in self.nodes}
        pred = {n: None for n in self.nodes}
        
        # Initialize roots
        for n in order:
            if self.in_degree.get(n, 0) == 0:
                dist[n] = 0.0
                
        for u in order:
            if dist[u] == -float('inf'): continue
            cost = self.nodes[u].estimated_cost
            for v in self.adj.get(u, []):
                if dist[u] + cost >= dist[v]:
                    dist[v] = dist[u] + cost
                    pred[v] = u
                    
        valid_nodes = [n for n in order if dist[n] > -float('inf')]
        if not valid_nodes: return [], 0.0
        
        # Tie-break by topological index to ensure terminal nodes are preferred
        end_node = max(valid_nodes, key=lambda n: (dist[n], order.index(n)))
        
        path = []
        curr = end_node
        while curr is not None:
            path.append(curr)
            curr = pred[curr]
            
        return list(reversed(path)), max(0.0, dist[end_node])

    def traverse(self, start: str) -> List[str]:
        visited = set()
        q = deque([start])
        res = []
        while q:
            u = q.popleft()
            if u in visited: continue
            visited.add(u)
            res.append(u)
            for v in self.adj.get(u, []):
                if v not in visited:
                    q.append(v)
        return res
