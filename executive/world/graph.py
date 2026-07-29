"""Knowledge Graph: Directed, weighted graph with entity synchronization and integrity validation."""
import time
import uuid
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from .relationship import RelationshipManager

logger = logging.getLogger(__name__)

@dataclass
class GraphNode:
    """Represents a node in the knowledge graph, typically mirroring a WorldEntity."""
    id: str
    entity_type: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "entity_type": self.entity_type,
            "attributes": self.attributes, "metadata": self.metadata,
            "created_at": self.created_at, "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphNode":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class GraphEdge:
    """Represents a directed, weighted relationship between two nodes."""
    id: str
    source_id: str
    target_id: str
    rel_type: str
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "source_id": self.source_id, "target_id": self.target_id,
            "rel_type": self.rel_type, "weight": self.weight, "metadata": self.metadata,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphEdge":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class KnowledgeGraph:
    """Core graph structure managing nodes, edges, adjacency, and integrity."""
    def __init__(self, rel_manager: Optional[RelationshipManager] = None) -> None:
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[str, GraphEdge] = {}
        self.adj: Dict[str, List[str]] = {}
        self.rev_adj: Dict[str, List[str]] = {}
        self.rel_manager = rel_manager or RelationshipManager()
        self._edge_index: Dict[Tuple[str, str, str], str] = {}

    def add_node(self, node_id: str, entity_type: str = "", attributes: Dict[str, Any] = None, metadata: Dict[str, Any] = None) -> GraphNode:
        """Add or update a graph node."""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            if attributes: node.attributes.update(attributes)
            if metadata: node.metadata.update(metadata)
            node.updated_at = time.time()
            return node
        node = GraphNode(id=node_id, entity_type=entity_type, attributes=attributes or {}, metadata=metadata or {})
        self.nodes[node_id] = node
        self.adj.setdefault(node_id, [])
        self.rev_adj.setdefault(node_id, [])
        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all connected edges."""
        if node_id not in self.nodes:
            return False
        edges_to_remove = [eid for eid, e in self.edges.items() if e.source_id == node_id or e.target_id == node_id]
        for eid in edges_to_remove:
            self.remove_edge(eid)
        del self.nodes[node_id]
        self.adj.pop(node_id, None)
        self.rev_adj.pop(node_id, None)
        return True

    def add_edge(self, source_id: str, target_id: str, rel_type: str, weight: float = 1.0, metadata: Dict[str, Any] = None) -> Optional[GraphEdge]:
        """Add a directed, weighted edge. Prevents duplicates and dangling references."""
        if source_id not in self.nodes or target_id not in self.nodes:
            logger.warning("Dangling reference prevented: %s -> %s", source_id, target_id)
            return None
        if not self.rel_manager.is_valid_type(rel_type):
            logger.warning("Invalid relationship type: %s", rel_type)
            return None
        key = (source_id, target_id, rel_type)
        if key in self._edge_index:
            logger.debug("Duplicate edge prevented: %s -> %s (%s)", source_id, target_id, rel_type)
            return self.edges[self._edge_index[key]]

        edge_id = uuid.uuid4().hex[:12]
        edge = GraphEdge(id=edge_id, source_id=source_id, target_id=target_id, rel_type=rel_type, weight=weight, metadata=metadata or {})
        self.edges[edge_id] = edge
        self._edge_index[key] = edge_id
        self.adj.setdefault(source_id, []).append(target_id)
        self.rev_adj.setdefault(target_id, []).append(source_id)
        return edge

    def remove_edge(self, edge_id: str) -> bool:
        """Remove an edge by ID."""
        edge = self.edges.pop(edge_id, None)
        if not edge:
            return False
        key = (edge.source_id, edge.target_id, edge.rel_type)
        self._edge_index.pop(key, None)
        if edge.target_id in self.adj.get(edge.source_id, []):
            self.adj[edge.source_id].remove(edge.target_id)
        if edge.source_id in self.rev_adj.get(edge.target_id, []):
            self.rev_adj[edge.target_id].remove(edge.source_id)
        return True

    def get_neighbors(self, node_id: str, rel_type: Optional[str] = None) -> List[str]:
        """Retrieve outgoing neighbors, optionally filtered by relationship type."""
        if node_id not in self.adj:
            return []
        neighbors = []
        for tgt in self.adj[node_id]:
            if rel_type:
                if (node_id, tgt, rel_type) in self._edge_index:
                    neighbors.append(tgt)
            else:
                neighbors.append(tgt)
        return list(set(neighbors))

    def validate_integrity(self) -> List[str]:
        """Check for dangling references and structural inconsistencies."""
        issues = []
        for eid, edge in self.edges.items():
            if edge.source_id not in self.nodes:
                issues.append(f"Edge {eid} has dangling source {edge.source_id}")
            if edge.target_id not in self.nodes:
                issues.append(f"Edge {eid} has dangling target {edge.target_id}")
        return issues

    def sync_from_world_model(self, world_model: Any) -> None:
        """Synchronize graph nodes from WorldModel entities."""
        for eid, entity in world_model.state.entities.items():
            self.add_node(eid, entity.entity_type, entity.attributes, entity.metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph to dictionary."""
        return {
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "edges": {eid: e.to_dict() for eid, e in self.edges.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], rel_manager: Optional[RelationshipManager] = None) -> "KnowledgeGraph":
        """Deserialize graph from dictionary."""
        kg = cls(rel_manager)
        for nid, nd in data.get("nodes", {}).items():
            kg.nodes[nid] = GraphNode.from_dict(nd)
            kg.adj.setdefault(nid, [])
            kg.rev_adj.setdefault(nid, [])
        for eid, ed in data.get("edges", {}).items():
            edge = GraphEdge.from_dict(ed)
            kg.edges[eid] = edge
            kg._edge_index[(edge.source_id, edge.target_id, edge.rel_type)] = eid
            kg.adj.setdefault(edge.source_id, []).append(edge.target_id)
            kg.rev_adj.setdefault(edge.target_id, []).append(edge.source_id)
        return kg
