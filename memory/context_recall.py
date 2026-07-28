"""Context Recall Engine."""
import logging
from typing import List, Dict, Any
from .hybrid_search import HybridSearch
from .link_graph import MemoryGraph

logger = logging.getLogger(__name__)

class ContextRecallEngine:
    """Retrieves minimum relevant memories for current context."""
    
    def __init__(self, hybrid_search: HybridSearch, graph: MemoryGraph):
        self.search = hybrid_search
        self.graph = graph

    def retrieve_context(self, query: str, memories: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """General context retrieval."""
        return self.search.search(query, memories, top_k=limit)

    def goal_context(self, goal: str, memories: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve memories relevant to a specific goal."""
        direct = [m for m in memories if m.get("goal", "").lower() == goal.lower()]
        if len(direct) >= limit:
            return direct[:limit]
        semantic = self.search.search(goal, memories, top_k=limit - len(direct))
        return direct + semantic

    def project_context(self, project_tag: str, memories: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve memories tagged with a project."""
        tagged = [m for m in memories if project_tag.lower() in [t.lower() for t in m.get("tags", [])]]
        return tagged[:limit]

    def linked_context(self, memory_id: str, memories: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve context via graph links."""
        neighbors = self.graph.neighbors(memory_id)
        linked = [m for m in memories if m.get("id") in neighbors]
        return linked[:limit]
