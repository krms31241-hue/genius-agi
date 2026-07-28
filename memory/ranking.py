"""Memory Ranking Engine."""
import time
import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MemoryRanker:
    """Ranks memories by importance, similarity, recency, confidence, and success."""
    
    def __init__(self, 
                 w_similarity: float = 0.35,
                 w_importance: float = 0.25,
                 w_recency: float = 0.20,
                 w_confidence: float = 0.10,
                 w_success: float = 0.10):
        self.w_sim = w_similarity
        self.w_imp = w_importance
        self.w_rec = w_recency
        self.w_conf = w_confidence
        self.w_succ = w_success

    def rank(self, memories: List[Dict[str, Any]], query_similarity: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """Score and sort memories."""
        if not memories:
            return []
        
        now = time.time()
        scored = []
        
        for m in memories:
            mid = m.get("id", "")
            
            # Similarity
            sim = (query_similarity or {}).get(mid, 0.0)
            
            # Importance (fallback to confidence/frequency if not precomputed)
            imp = m.get("importance", m.get("confidence", 0.5))
            
            # Recency (exponential decay, half-life 7 days)
            ts = m.get("timestamp", m.get("updated_at", m.get("created_at", now)))
            age = now - ts
            recency = math.exp(-0.693 * age / 604800.0)
            
            # Confidence
            conf = m.get("confidence", 0.5)
            
            # Success history
            succ = 1.0 if m.get("success", True) else 0.0
            
            final_score = (sim * self.w_sim + 
                           imp * self.w_imp + 
                           recency * self.w_rec + 
                           conf * self.w_conf + 
                           succ * self.w_succ)
            
            scored.append((m, final_score))
            
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored]
