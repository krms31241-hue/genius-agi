"""Goal Tree: Hierarchical dependency graph, completion propagation, merging, and reprioritization."""
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional
from collections import deque

logger = logging.getLogger(__name__)

class NodeType(str, Enum):
    MISSION = "mission"
    CAMPAIGN = "campaign"
    OBJECTIVE = "objective"
    GOAL = "goal"
    TASK = "task"
    ACTION = "action"

class NodeStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class HierarchyNode:
    id: str
    node_type: NodeType
    title: str
    status: NodeStatus = NodeStatus.PENDING
    priority: float = 0.0
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

class GoalTree:
    """Manages planning hierarchy, DAG dependencies, completion bubbling, and dynamic priority."""
    def __init__(self):
        self.nodes: Dict[str, HierarchyNode] = {}
        self.adj: Dict[str, List[str]] = {}
        self.rev_adj: Dict[str, List[str]] = {}

    def add_node(self, node: HierarchyNode) -> bool:
        if node.id in self.nodes:
            return False
        self.nodes[node.id] = node
        self.adj.setdefault(node.id, [])
        self.rev_adj.setdefault(node.id, [])
        if node.parent_id and node.parent_id in self.nodes:
            self.nodes[node.parent_id].children.append(node.id)
        for dep in node.dependencies:
            self.adj.setdefault(dep, []).append(node.id)
            self.rev_adj.setdefault(node.id, []).append(dep)
        node.updated_at = time.time()
        return True

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        return {k: list(v) for k, v in self.adj.items()}

    def detect_cycles(self) -> bool:
        visited = set()
        rec_stack = set()
        def dfs(u: str) -> bool:
            visited.add(u)
            rec_stack.add(u)
            for v in self.adj.get(u, []):
                if v not in visited:
                    if dfs(v): return True
                elif v in rec_stack: return True
            rec_stack.discard(u)
            return False
        return any(dfs(n) for n in self.nodes if n not in visited)

    def topological_sort(self) -> List[str]:
        if self.detect_cycles():
            raise ValueError("Dependency cycle detected")
        in_degree = {n: len(self.rev_adj.get(n, [])) for n in self.nodes}
        queue = deque([n for n, d in in_degree.items() if d == 0])
        order = []
        while queue:
            u = queue.popleft()
            order.append(u)
            for v in self.adj.get(u, []):
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        return order

    def propagate_completion(self, node_id: str) -> List[str]:
        if node_id not in self.nodes:
            return []
        node = self.nodes[node_id]
        if node.status == NodeStatus.COMPLETED:
            return []
        node.status = NodeStatus.COMPLETED
        node.progress = 1.0
        node.updated_at = time.time()
        propagated = [node_id]

        if node.parent_id and node.parent_id in self.nodes:
            parent = self.nodes[node.parent_id]
            children = [c for c in parent.children if c in self.nodes]
            if children and all(self.nodes[c].status == NodeStatus.COMPLETED for c in children):
                propagated.extend(self.propagate_completion(node.parent_id))
        return propagated

    def reprioritize(self, context: Dict[str, Any] = None) -> None:
        context = context or {}
        urgency_mult = context.get("urgency_multiplier", 1.0)
        for node in self.nodes.values():
            if node.status in (NodeStatus.COMPLETED, NodeStatus.CANCELLED, NodeStatus.FAILED):
                continue
            base = node.priority
            dep_penalty = len(node.dependencies) * 0.05
            depth_bonus = 0.1 if node.node_type in (NodeType.ACTION, NodeType.TASK) else 0.0
            node.priority = max(0.0, min(100.0, (base - dep_penalty + depth_bonus) * urgency_mult))
            node.updated_at = time.time()

    def merge_goals(self, goal_ids: List[str], new_goal_id: str, new_title: str) -> bool:
        valid = [gid for gid in goal_ids if gid in self.nodes]
        if not valid:
            return False
        merged_deps = set()
        merged_children = set()
        max_priority = 0.0
        parent_id = None
        for gid in valid:
            n = self.nodes[gid]
            merged_deps.update(n.dependencies)
            merged_children.update(n.children)
            max_priority = max(max_priority, n.priority)
            parent_id = parent_id or n.parent_id
            del self.nodes[gid]

        new_node = HierarchyNode(
            id=new_goal_id, node_type=NodeType.GOAL, title=new_title,
            priority=max_priority, parent_id=parent_id,
            children=list(merged_children), dependencies=list(merged_deps - {new_goal_id})
        )
        self.add_node(new_node)
        if parent_id and parent_id in self.nodes:
            self.nodes[parent_id].children = [c for c in self.nodes[parent_id].children if c not in valid]
            self.nodes[parent_id].children.append(new_goal_id)
        return True

    def get_hierarchy(self) -> List[Dict[str, Any]]:
        def build_tree(nid: str) -> Dict[str, Any]:
            n = self.nodes[nid]
            return {
                "id": n.id, "type": n.node_type.value, "title": n.title,
                "status": n.status.value, "priority": n.priority,
                "children": [build_tree(c) for c in n.children if c in self.nodes]
            }
        roots = [nid for nid, n in self.nodes.items() if n.parent_id is None or n.parent_id not in self.nodes]
        return [build_tree(r) for r in roots]
