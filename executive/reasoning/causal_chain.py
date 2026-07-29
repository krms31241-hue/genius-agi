"""Causal Chain Builder: Constructs and scores causal paths."""
import logging
from typing import Dict, List, Optional, Set
from .causal_graph import CausalGraph
from .reasoning_models import CausalChain, CausalRelation

logger = logging.getLogger(__name__)

class CausalChainBuilder:
    """Traverses causal graph to build complete chains from roots to effects."""
    def __init__(self, graph: CausalGraph) -> None:
        self.graph = graph

    def trace_back(self, effect_id: str, max_depth: int = 5) -> List[CausalChain]:
        """Find all causal chains leading to an effect."""
        chains: List[CausalChain] = []
        self._dfs_backward(effect_id, [], [], set(), max_depth, chains)
        return chains

    def trace_forward(self, cause_id: str, max_depth: int = 5) -> List[CausalChain]:
        """Find all causal chains originating from a cause."""
        chains: List[CausalChain] = []
        self._dfs_forward(cause_id, [], [], set(), max_depth, chains)
        return chains

    def _dfs_backward(self, current: str, path_nodes: List[str], path_rels: List[str],
                      visited: Set[str], depth: int, chains: List[CausalChain]) -> None:
        if current in visited or depth <= 0:
            return
        visited.add(current)
        path_nodes.append(current)
        
        causes = self.graph.get_direct_causes(current)
        if not causes:
            # Root reached
            chain = CausalChain(
                nodes=list(reversed(path_nodes)),
                relations=list(reversed(path_rels)),
                root_cause_id=path_nodes[-1],
                final_effect_id=path_nodes[0],
                confidence=self._calc_confidence(path_rels)
            )
            chains.append(chain)
        else:
            for rel in causes:
                if rel.relation_type == "prevents":
                    continue # Skip prevention links in backward causal tracing
                path_rels.append(rel.id)
                self._dfs_backward(rel.cause_id, path_nodes, path_rels, visited, depth - 1, chains)
                path_rels.pop()
        
        path_nodes.pop()
        visited.discard(current)

    def _dfs_forward(self, current: str, path_nodes: List[str], path_rels: List[str],
                     visited: Set[str], depth: int, chains: List[CausalChain]) -> None:
        if current in visited or depth <= 0:
            return
        visited.add(current)
        path_nodes.append(current)
        
        effects = self.graph.get_direct_effects(current)
        if not effects:
            # Leaf reached
            chain = CausalChain(
                nodes=list(path_nodes),
                relations=list(path_rels),
                root_cause_id=path_nodes[0],
                final_effect_id=path_nodes[-1],
                confidence=self._calc_confidence(path_rels)
            )
            chains.append(chain)
        else:
            for rel in effects:
                if rel.relation_type == "prevents":
                    continue
                path_rels.append(rel.id)
                self._dfs_forward(rel.effect_id, path_nodes, path_rels, visited, depth - 1, chains)
                path_rels.pop()
        
        path_nodes.pop()
        visited.discard(current)

    def _calc_confidence(self, rel_ids: List[str]) -> float:
        if not rel_ids:
            return 1.0
        conf = 1.0
        for rid in rel_ids:
            rel = self.graph.relations.get(rid)
            if rel:
                conf *= rel.confidence
        return max(0.01, conf)
