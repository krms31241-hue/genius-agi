"""Importance Scoring Engine for Memory Entities."""
import time
import math
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ImportanceScorer:
    """Evaluates memory importance on a 0-100 scale.
    Factors: frequency, recency, success history, user feedback."""
    
    def __init__(self, 
                 weight_frequency: float = 0.25,
                 weight_recency: float = 0.25,
                 weight_success: float = 0.25,
                 weight_feedback: float = 0.25,
                 recency_half_life: float = 86400.0):
        self.w_freq = weight_frequency
        self.w_rec = weight_recency
        self.w_succ = weight_success
        self.w_feed = weight_feedback
        self.half_life = recency_half_life

    def score(self, memory_data: Dict[str, Any]) -> float:
        """Calculate importance score between 0 and 100."""
        try:
            freq_score = self._calc_frequency(memory_data.get("frequency", 1))
            rec_score = self._calc_recency(memory_data.get("timestamp", time.time()), memory_data.get("last_access", time.time()))
            succ_score = self._calc_success(memory_data.get("success_count", 0), memory_data.get("failure_count", 0))
            feed_score = self._calc_feedback(memory_data.get("feedback", 0.5))
            
            raw = (freq_score * self.w_freq + 
                   rec_score * self.w_rec + 
                   succ_score * self.w_succ + 
                   feed_score * self.w_feed)
            
            return max(0.0, min(100.0, raw * 100.0))
        except Exception as e:
            logger.error("Importance scoring failed: %s", e)
            return 0.0

    def _calc_frequency(self, count: int) -> float:
        """Logarithmic scaling: 1->0.2, 10->0.5, 100->0.8, 1000->1.0"""
        return min(1.0, math.log10(max(1, count)) / 3.0)

    def _calc_recency(self, created: float, last_access: float) -> float:
        """Exponential decay based on age and last access."""
        age = time.time() - max(created, last_access)
        decay = math.exp(-0.693 * age / self.half_life)
        return max(0.0, min(1.0, decay))

    def _calc_success(self, successes: int, failures: int) -> float:
        """Success ratio with smoothing."""
        total = successes + failures
        if total == 0:
            return 0.5
        return successes / total

    def _calc_feedback(self, feedback: float) -> float:
        """Normalize explicit feedback to 0-1."""
        try:
            return max(0.0, min(1.0, float(feedback)))
        except (ValueError, TypeError):
            return 0.5
