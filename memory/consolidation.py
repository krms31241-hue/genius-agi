"""Memory Consolidation Engine."""
import time
import logging
from typing import Any, Dict, List, Optional
from .memory_models import Experience, Fact

logger = logging.getLogger(__name__)

class MemoryConsolidator:
    """Moves important information from Working Memory to Long-Term Memory.
    Decides promotion, applies forgetting, and prepares replay."""
    
    def __init__(self, 
                 manager: Any, 
                 scorer: Any, 
                 policy: Any, 
                 stats: Any,
                 promotion_threshold: float = 65.0):
        self.manager = manager
        self.scorer = scorer
        self.policy = policy
        self.stats = stats
        self.threshold = promotion_threshold

    def should_consolidate(self, memory_data: Dict[str, Any]) -> bool:
        """Determine if a memory deserves long-term storage."""
        score = self.scorer.score(memory_data)
        return score >= self.threshold

    def promote(self, memory_data: Dict[str, Any], target: str = "episodic") -> bool:
        """Promote working memory to episodic or semantic storage."""
        try:
            if target == "episodic":
                exp = Experience(
                    goal=memory_data.get("goal", ""),
                    action=memory_data.get("action", "consolidated"),
                    result=memory_data.get("result", ""),
                    success=memory_data.get("success", False),
                    duration=memory_data.get("duration", 0.0),
                    metadata=memory_data.get("metadata", {})
                )
                success = self.manager.add_experience(exp)
            elif target == "semantic":
                fact = Fact(
                    title=memory_data.get("title", "Consolidated Fact"),
                    content=memory_data.get("content", ""),
                    source=memory_data.get("source", "consolidation"),
                    confidence=memory_data.get("confidence", 0.7),
                    tags=memory_data.get("tags", [])
                )
                success = self.manager.add_fact(fact)
            else:
                return False
                
            if success:
                self.stats.increment("promoted_count")
                logger.info("Promoted memory to %s: %s", target, memory_data.get("id", "unknown"))
            return success
        except Exception as e:
            logger.error("Promotion failed: %s", e)
            return False

    def consolidate(self, working_keys: Optional[List[str]] = None) -> Dict[str, int]:
        """Scan working memory, score, promote, and apply forgetting."""
        results = {"scanned": 0, "promoted": 0, "forgotten": 0}
        
        # If no keys provided, we simulate scanning known working items
        # In production, working memory keys are tracked or iterated via a registry
        keys_to_check = working_keys or []
        
        for key in keys_to_check:
            data = self.manager.get_working(key)
            if data is None:
                continue
            results["scanned"] += 1
            
            if isinstance(data, dict):
                data["id"] = key
                data["timestamp"] = data.get("timestamp", time.time())
                data["last_access"] = time.time()
                
                if self.should_consolidate(data):
                    target = "semantic" if data.get("type") == "fact" else "episodic"
                    if self.promote(data, target):
                        results["promoted"] += 1
                        self.manager.clear_working() # Clear after successful promotion batch
        
        # Apply forgetting policy to episodic memory
        recent = self.manager.recent_experiences(limit=100)
        mem_dicts = [e.to_dict() for e in recent]
        to_forget = self.policy.get_candidates(mem_dicts)
        if to_forget:
            self.stats.increment("forgotten_count", len(to_forget))
            results["forgotten"] = len(to_forget)
            
        return results

    def replay(self, mode: str = "recent", limit: int = 5) -> List[Any]:
        """Prepare replay batch for reinforcement learning."""
        from .replay import ReplayEngine
        engine = ReplayEngine(self.manager)
        self.stats.increment("replay_count")
        
        if mode == "failures":
            return engine.replay_failures(limit)
        elif mode == "successes":
            return engine.replay_successes(limit)
        elif mode == "random":
            return engine.replay_random(limit)
        return engine.replay_recent(limit)
