"""Hybrid Search Engine."""
import logging
from typing import List, Dict, Any, Tuple
from .vectorizer import MemoryVectorizer
from .semantic_search import SemanticSearch
from .ranking import MemoryRanker

logger = logging.getLogger(__name__)

class HybridSearch:
    """Combines keyword matching, semantic similarity, and metadata ranking."""
    
    def __init__(self, vectorizer: MemoryVectorizer, ranker: MemoryRanker):
        self.vectorizer = vectorizer
        self.semantic = SemanticSearch(vectorizer)
        self.ranker = ranker

    def _keyword_score(self, query: str, text: str) -> float:
        """Simple normalized keyword overlap score."""
        if not query or not text:
            return 0.0
        q_tokens = set(query.lower().split())
        t_tokens = set(text.lower().split())
        if not q_tokens:
            return 0.0
        overlap = len(q_tokens & t_tokens)
        return overlap / len(q_tokens)

    def search(self, query: str, memories: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
        """Execute hybrid search and return ranked memories."""
        if not memories or not query:
            return []
            
        # 1. Semantic scoring
        sem_results = self.semantic.search(query, memories, top_k=len(memories))
        sim_map = {m.get("id", ""): score for m, score in sem_results}
        
        # 2. Keyword boosting
        for m in memories:
            text = " ".join(str(m.get(k, "")) for k in ["goal", "content", "title", "action", "result"])
            kw_score = self._keyword_score(query, text)
            mid = m.get("id", "")
            # Blend semantic and keyword scores
            sim_map[mid] = max(sim_map.get(mid, 0.0), kw_score * 0.8)
            
        # 3. Final ranking
        return self.ranker.rank(memories, query_similarity=sim_map)[:top_k]
