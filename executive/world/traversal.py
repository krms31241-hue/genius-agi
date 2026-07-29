"""Traversal Engine: BFS, DFS, Shortest Path, Components, Reachability, Ancestors/Descendants."""
import heapq
import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import deque
from .graph import KnowledgeGraph

logger = logging.getLogger(__name__)

class TraversalEngine:
    """Deterministic graph traversal algorithms."""
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph

    def bfs(self, start_id: str, max_depth: int = -1) -> List[str]:
        """Breadth-First Search traversal."""
        if start_id not in self.graph.nodes:
            return []
        visited: Set[str] = set()
        queue = deque([(start_id, 0)])
        order: List[str] = []
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            order.append(node)
            if max_depth != -1 and depth >= max_depth:
                continue
            for neighbor in self.graph.adj.get(node, []):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        return order

    def dfs(self, start_id: str, max_depth: int = -1) -> List[str]:
        """Depth-First Search traversal."""
        if start_id not in self.graph.nodes:
            return []
        visited: Set[str] = set()
        stack = [(start_id, 0)]
        order: List[str] = []
        while stack:
            node, depth = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            order.append(node)
            if max_depth != -1 and depth >= max_depth:
                continue
            for neighbor in reversed(self.graph.adj.get(node, [])):
                if neighbor not in visited:
                    stack.append((neighbor, depth + 1))
        return order

    def shortest_path(self, start_id: str, end_id: str) -> Tuple[List[str], float]:
        """Dijkstra's algorithm for weighted shortest path."""
        if start_id not in self.graph.nodes or end_id not in self.graph.nodes:
            return [], float('inf')
        dist: Dict[str, float] = {start_id: 0.0}
        prev: Dict[str, Optional[str]] = {start_id: None}
        pq: List[Tuple[float, str]] = [(0.0, start_id)]
        visited: Set[str] = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == end_id:
                break
            for v in self.graph.adj.get(u, []):
                weight = 1.0
                for eid, edge in self.graph.edges.items():
                    if edge.source_id == u and edge.target_id == v:
                        weight = edge.weight
                        break
                new_dist = d + weight
                if new_dist < dist.get(v, float('inf')):
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(pq, (new_dist, v))

        if end_id not in prev:
            return [], float('inf')
        path: List[str] = []
        curr: Optional[str] = end_id
        while curr is not None:
            path.append(curr)
            curr = prev[curr]
        return list(reversed(path)), dist[end_id]

    def connected_components(self) -> List[Set[str]]:
        """Find connected components treating graph as undirected."""
        visited: Set[str] = set()
        components: List[Set[str]] = []
        undirected_adj: Dict[str, Set[str]] = {n: set() for n in self.graph.nodes}
        for u in self.graph.nodes:
            for v in self.graph.adj.get(u, []):
                undirected_adj[u].add(v)
                undirected_adj[v].add(u)

        for node in self.graph.nodes:
            if node not in visited:
                comp: Set[str] = set()
                stack = [node]
                while stack:
                    u = stack.pop()
                    if u not in visited:
                        visited.add(u)
                        comp.add(u)
                        for v in undirected_adj.get(u, []):
                            if v not in visited:
                                stack.append(v)
                components.append(comp)
        return components

    def is_reachable(self, start_id: str, end_id: str) -> bool:
        """Check if end_id is reachable from start_id."""
        path, _ = self.shortest_path(start_id, end_id)
        return len(path) > 0

    def ancestors(self, node_id: str) -> List[str]:
        """Find all ancestors via reverse edges."""
        if node_id not in self.graph.nodes:
            return []
        visited: Set[str] = set()
        stack = [node_id]
        ancestors: List[str] = []
        while stack:
            u = stack.pop()
            for v in self.graph.rev_adj.get(u, []):
                if v not in visited:
                    visited.add(v)
                    ancestors.append(v)
                    stack.append(v)
        return ancestors

    def descendants(self, node_id: str) -> List[str]:
        """Find all descendants via forward edges."""
        if node_id not in self.graph.nodes:
            return []
        visited: Set[str] = set()
        stack = [node_id]
        descendants: List[str] = []
        while stack:
            u = stack.pop()
            for v in self.graph.adj.get(u, []):
                if v not in visited:
                    visited.add(v)
                    descendants.append(v)
                    stack.append(v)
        return descendants

    def expand_relationships(self, node_id: str, rel_types: Optional[List[str]] = None) -> List[str]:
        """Expand neighbors filtered by specific relationship types."""
        neighbors: List[str] = []
        for tgt in self.graph.adj.get(node_id, []):
            for (s, t, r) in self.graph._edge_index.keys():
                if s == node_id and t == tgt:
                    if rel_types is None or r in rel_types:
                        neighbors.append(tgt)
                        break
        return list(set(neighbors))
