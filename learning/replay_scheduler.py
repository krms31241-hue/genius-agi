"""Replay Scheduler: Orchestrates sampling strategies and decay application."""
import logging
from typing import List, Dict, Any, Optional
from .replay_buffer import ReplayBuffer
from .experience import Experience

logger = logging.getLogger(__name__)

class ReplayScheduler:
    """Deterministic scheduler that selects replay strategies and manages sampling."""
    
    def __init__(self, buffer: ReplayBuffer, default_strategy: str = "prioritized") -> None:
        self.buffer = buffer
        self.default_strategy = default_strategy
        self.strategies = {
            "random": self.buffer.sample_random,
            "prioritized": self.buffer.sample_prioritized,
            "success": self.buffer.sample_success,
            "failure": self.buffer.sample_failure
        }

    def schedule_replay(self, n: int, strategy: Optional[str] = None, decay: float = 0.99) -> List[Experience]:
        """Execute a replay sampling cycle using the specified strategy."""
        strat = strategy or self.default_strategy
        sampler = self.strategies.get(strat)
        if not sampler:
            logger.warning("Unknown strategy %s, falling back to random", strat)
            sampler = self.buffer.sample_random
        
        if strat == "prioritized":
            return sampler(n, decay_factor=decay)
        return sampler(n)

    def get_statistics(self) -> Dict[str, Any]:
        """Return current replay metrics."""
        return self.buffer.metrics.to_dict()
