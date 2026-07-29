"""Graph Query Engine: High-level querying interface for the Knowledge Graph."""
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from .graph import KnowledgeGraph, GraphNode
from .traversal import TraversalEngine

logger = logging.getLogger(__name__)

class GraphQueryEngine:
    """Provides semantic query capabilities over the knowledge graph."""
    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        self.traversal = TraversalEngine(graph)

    def find_by_id(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve node by ID."""
        return self.graph.nodes.get(node_id)

    def find_by_type(self, entity_type: str) -> List[GraphNode]:
        """Find all nodes of a specific entity type."""
        return [n for n in self.graph.nodes.values() if n.entity_type == entity_type]

    def find_neighbors(self, node_id: str, rel_type: Optional[str] = None) -> List[GraphNode]:
        """Retrieve neighbor nodes, optionally filtered by relationship type."""
        neighbor_ids = self.graph.get_neighbors(node_id, rel_type)
        return [self.graph.nodes[nid] for nid in neighbor_ids if nid in self.graph.nodes]

    def find_relationship(self, source_id: str, target_id: str) -> List[Dict[str, Any]]:
        """Find all relationships between two nodes."""
        edges = []
        for eid, edge in self.graph.edges.items():
            if edge.source_id == source_id and edge.target_id == target_id:
                edges.append(edge.to_dict())
        return edges

    def find_shortest_path(self, start_id: str, end_id: str) -> Tuple[List[str], float]:
        """Compute shortest path between two nodes."""
        return self.traversal.shortest_path(start_id, end_id)

    def find_connected_entities(self, node_id: str) -> Set[str]:
        """Return all entities in the same connected component."""
        components = self.traversal.connected_components()
        for comp in components:
            if node_id in comp:
                return comp
        return set()

    def find_isolated_entities(self) -> List[GraphNode]:
        """Find nodes with no incoming or outgoing edges."""
        isolated = []
        for nid, node in self.graph.nodes.items():
            if not self.graph.adj.get(nid) and not self.graph.rev_adj.get(nid):
                isolated.append(node)
        return isolated

    def get_statistics(self) -> Dict[str, Any]:
        """Compute graph topology statistics."""
        num_nodes = len(self.graph.nodes)
        num_edges = len(self.graph.edges)
        avg_degree = (sum(len(v) for v in self.graph.adj.values()) / max(1, num_nodes))
        components = len(self.traversal.connected_components())
        return {
            "nodes": num_nodes,
            "edges": num_edges,
            "avg_degree": round(avg_degree, 2),
            "connected_components": components,
            "density": round(num_edges / max(1, num_nodes * (num_nodes - 1)), 4)
        }
