"""Root Cause Analyzer: Identifies and ranks likely origins of observed effects."""
import logging
from typing import Dict, Any, List, Set
from collections import defaultdict
from .causal_graph import CausalGraph
from .causal_chain import CausalChainBuilder
from .reasoning_models import CausalChain

logger = logging.getLogger(__name__)

class RootCauseAnalyzer:
    """Analyzes symptoms to find, rank, and explain root causes."""
    def __init__(self, graph: CausalGraph, chain_builder: CausalChainBuilder) -> None:
        self.graph = graph
        self.builder = chain_builder

    def analyze(self, effect_ids: List[str], max_depth: int = 5) -> List[Dict[str, Any]]:
        """Find and rank root causes for a set of observed effects."""
        cause_scores: Dict[str, float] = defaultdict(float)
        cause_explanations: Dict[str, List[str]] = defaultdict(list)
        cause_chains: Dict[str, List[CausalChain]] = defaultdict(list)

        for eid in effect_ids:
            chains = self.builder.trace_back(eid, max_depth)
            for chain in chains:
                root = chain.root_cause_id
                # Score by confidence and number of explained effects
                score = chain.confidence * (1.0 + 0.5 * len(effect_ids))
                cause_scores[root] += score
                cause_explanations[root].append(f"Causes {eid} via chain confidence {chain.confidence:.2f}")
                cause_chains[root].append(chain)

        ranked = sorted(cause_scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for cause_id, score in ranked:
            results.append({
                "cause_id": cause_id,
                "score": round(score, 3),
                "explanations": cause_explanations[cause_id],
                "chains": [c.to_dict() for c in cause_chains[cause_id][:3]] # Top 3 chains per cause
            })
        return results

    def find_cascading_failures(self, root_id: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """Identify downstream cascade effects from a single root."""
        chains = self.builder.trace_forward(root_id, max_depth)
        affected: Dict[str, float] = defaultdict(float)
        for chain in chains:
            for node in chain.nodes[1:]:
                affected[node] = max(affected[node], chain.confidence)
        return [{"entity_id": eid, "impact_confidence": round(conf, 3)} for eid, conf in sorted(affected.items(), key=lambda x: x[1], reverse=True)]
