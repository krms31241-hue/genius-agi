"""Replay Engine for Memory Recall."""
import random
import logging
from typing import List, Any, Optional

logger = logging.getLogger(__name__)

class ReplayEngine:
    """Provides structured recall of past experiences."""
    
    def __init__(self, manager: Any):
        self.manager = manager

    def replay_recent(self, limit: int = 10) -> List[Any]:
        """Replay most recent experiences."""
        try:
            return self.manager.recent_experiences(limit=limit)
        except Exception as e:
            logger.error("Replay recent failed: %s", e)
            return []

    def replay_failures(self, limit: int = 10) -> List[Any]:
        """Replay past failures for learning."""
        try:
            return self.manager.search_experiences(success=False, limit=limit)
        except Exception as e:
            logger.error("Replay failures failed: %s", e)
            return []

    def replay_successes(self, limit: int = 10) -> List[Any]:
        """Replay past successes for reinforcement."""
        try:
            return self.manager.search_experiences(success=True, limit=limit)
        except Exception as e:
            logger.error("Replay successes failed: %s", e)
            return []

    def replay_random(self, limit: int = 10) -> List[Any]:
        """Replay random experiences for diversity."""
        try:
            all_exp = self.manager.recent_experiences(limit=100)
            if not all_exp:
                return []
            sampled = random.sample(all_exp, min(limit, len(all_exp)))
            return sampled
        except Exception as e:
            logger.error("Replay random failed: %s", e)
            return []

    def replay_by_goal(self, goal: str, limit: int = 10) -> List[Any]:
        """Replay experiences related to a specific goal."""
        try:
            return self.manager.search_experiences(goal=goal, limit=limit)
        except Exception as e:
            logger.error("Replay by goal failed: %s", e)
            return []
