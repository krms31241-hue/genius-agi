"""Forgetting Policy Engine."""
import time
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ForgettingPolicy:
    """Determines which memories should expire based on TTL, LRU, LFU, and decay."""
    
    def __init__(self, 
                 ttl_seconds: float = 604800.0,  # 7 days default
                 lru_limit: int = 5000,
                 lfu_limit: int = 3000,
                 decay_rate: float = 0.05):
        self.ttl = ttl_seconds
        self.lru_limit = lru_limit
        self.lfu_limit = lfu_limit
        self.decay_rate = decay_rate

    def should_expire(self, memory_data: Dict[str, Any]) -> bool:
        """Check if a single memory should be forgotten."""
        try:
            now = time.time()
            created = memory_data.get("timestamp", now)
            last_access = memory_data.get("last_access", created)
            age = now - created
            idle = now - last_access
            
            # TTL check
            if age > self.ttl:
                return True
            # Idle decay check
            if idle > (self.ttl * 0.5):
                return True
            return False
        except Exception as e:
            logger.error("Forgetting check failed: %s", e)
            return False

    def apply_lru(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Return IDs of least recently used memories exceeding limit."""
        if len(memories) <= self.lru_limit:
            return []
        sorted_mems = sorted(memories, key=lambda m: m.get("last_access", 0))
        excess = len(memories) - self.lru_limit
        return [m.get("id", "") for m in sorted_mems[:excess]]

    def apply_lfu(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Return IDs of least frequently used memories exceeding limit."""
        if len(memories) <= self.lfu_limit:
            return []
        sorted_mems = sorted(memories, key=lambda m: m.get("frequency", 0))
        excess = len(memories) - self.lfu_limit
        return [m.get("id", "") for m in sorted_mems[:excess]]

    def apply_decay(self, importance: float, age_seconds: float) -> float:
        """Reduce importance score over time."""
        decay_factor = max(0.0, 1.0 - (self.decay_rate * (age_seconds / 86400.0)))
        return max(0.0, importance * decay_factor)

    def get_candidates(self, memories: List[Dict[str, Any]]) -> List[str]:
        """Combine policies to return IDs safe to forget."""
        to_forget = set()
        for m in memories:
            if self.should_expire(m):
                to_forget.add(m.get("id", ""))
        to_forget.update(self.apply_lru(memories))
        to_forget.update(self.apply_lfu(memories))
        return list(to_forget)
