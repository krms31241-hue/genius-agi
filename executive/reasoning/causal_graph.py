"""Causal Graph: Directed graph managing causal relations and structural integrity."""
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from collections import defaultdict
from .reasoning_models import CausalRelation, CausalType

logger = logging.getLogger(__name__)

class CausalGraph:
    """Manages causal topology, validates references, and detects cycles."""
    def __init__(self) -> None:
        self.relations: Dict[str, CausalRelation] = {}
        self.adj: Dict[str, List[str]] = defaultdict(list)
        self.rev_adj: Dict[str, List[str]] = defaultdict(list)
        self._edge_index: Dict[Tuple[str, str, str], str] = {}

    def add_relation(self, rel: CausalRelation) -> bool:
        """Register a causal relation. Prevents duplicates."""
        key = (rel.cause_id, rel.effect_id, rel.relation_type)
        if key in self._edge_index:
            logger.debug("Duplicate causal relation prevented: %s -> %s (%s)", rel.cause_id, rel.effect_id, rel.relation_type)
            return False
        self.relations[rel.id] = rel
        self._edge_index[key] = rel.id
        self.adj[rel.cause_id].append(rel.effect_id)
        self.rev_adj[rel.effect_id].append(rel.cause_id)
        return True

    def remove_relation(self, rel_id: str) -> bool:
        """Remove a causal relation by ID."""
        rel = self.relations.pop(rel_id, None)
        if not rel:
            return False
        key = (rel.cause_id, rel.effect_id, rel.relation_type)
        self._edge_index.pop(key, None)
        if rel.effect_id in self.adj.get(rel.cause_id, []):
            self.adj[rel.cause_id].remove(rel.effect_id)
        if rel.cause_id in self.rev_adj.get(rel.effect_id, []):
            self.rev_adj[rel.effect_id].remove(rel.cause_id)
        return True

    def get_direct_causes(self, effect_id: str) -> List[CausalRelation]:
        """Retrieve relations where effect_id is the target."""
        causes = []
        for cause_id in self.rev_adj.get(effect_id, []):
            for rel_type in [CausalType.CAUSES, CausalType.ENABLES, CausalType.PREVENTS, CausalType.CORRELATES]:
                key = (cause_id, effect_id, rel_type)
                if key in self._edge_index:
                    causes.append(self.relations[self._edge_index[key]])
        return causes

    def get_direct_effects(self, cause_id: str) -> List[CausalRelation]:
        """Retrieve relations where cause_id is the source."""
        effects = []
        for effect_id in self.adj.get(cause_id, []):
            for rel_type in [CausalType.CAUSES, CausalType.ENABLES, CausalType.PREVENTS, CausalType.CORRELATES]:
                key = (cause_id, effect_id, rel_type)
                if key in self._edge_index:
                    effects.append(self.relations[self._edge_index[key]])
        return effects

    def detect_cycles(self) -> List[List[str]]:
        """Detect circular causality using DFS."""
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        cycles: List[List[str]] = []
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in self.adj.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    idx = path.index(neighbor)
                    cycles.append(path[idx:] + [neighbor])
            path.pop()
            rec_stack.discard(node)

        all_nodes = set(self.adj.keys()) | set(self.rev_adj.keys())
        for node in all_nodes:
            if node not in visited:
                dfs(node)
        return cycles

    def validate_references(self, valid_ids: Set[str]) -> List[str]:
        """Check for dangling references against a known set of entity IDs."""
        issues = []
        for rel in self.relations.values():
            if rel.cause_id not in valid_ids:
                issues.append(f"Dangling cause: {rel.cause_id} in relation {rel.id}")
            if rel.effect_id not in valid_ids:
                issues.append(f"Dangling effect: {rel.effect_id} in relation {rel.id}")
        return issues

    def to_dict(self) -> Dict[str, Any]:
        return {"relations": {rid: r.to_dict() for rid, r in self.relations.items()}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalGraph":
        graph = cls()
        for rid, rd in data.get("relations", {}).items():
            rel = CausalRelation.from_dict(rd)
            graph.add_relation(rel)
        return graph
