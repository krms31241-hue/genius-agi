"""Semantic Search Engine."""
import logging
from typing import List, Dict, Any, Tuple
from .vectorizer import MemoryVectorizer

logger = logging.getLogger(__name__)

class SemanticSearch:
    """Retrieves memories by meaning using vector similarity."""
    
    def __init__(self, vectorizer: MemoryVectorizer):
        self.vectorizer = vectorizer

    def _extract_text(self, memory: Dict[str, Any]) -> str:
        """Extract searchable text from a memory object/dict."""
        parts = [
            memory.get("goal", ""),
            memory.get("action", ""),
            memory.get("result", ""),
            memory.get("content", ""),
            memory.get("title", ""),
            memory.get("description", "")
        ]
        return " ".join(str(p) for p in parts if p)

    def search(self, query: str, memories: List[Dict[str, Any]], top_k: int = 5, threshold: float = 0.0) -> List[Tuple[Dict[str, Any], float]]:
        """Search memories by semantic similarity to query."""
        if not memories or not query:
            return []
        
        q_vec = self.vectorizer.vectorize(query)
        scored = []
        
        for mem in memories:
            text = self._extract_text(mem)
            m_vec = self.vectorizer.vectorize(text)
            sim = self.vectorizer.similarity(q_vec, m_vec)
            if sim >= threshold:
                scored.append((mem, sim))
                
        return self.rank_results(scored)[:top_k]

    def nearest(self, query: str, memories: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], float]:
        """Find single nearest memory."""
        res = self.search(query, memories, top_k=1)
        return res[0] if res else ({}, 0.0)

    def threshold_search(self, query: str, memories: List[Dict[str, Any]], threshold: float = 0.5) -> List[Tuple[Dict[str, Any], float]]:
        """Return all memories above similarity threshold."""
        return self.search(query, memories, top_k=len(memories), threshold=threshold)

    def rank_results(self, scored_memories: List[Tuple[Dict[str, Any], float]]) -> List[Tuple[Dict[str, Any], float]]:
        """Sort by similarity descending."""
        return sorted(scored_memories, key=lambda x: x[1], reverse=True)
