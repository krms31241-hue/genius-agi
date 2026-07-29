"""Skill Metrics Tracker: Deterministic running averages and confidence scaling."""
import time
import logging
from .skill import Skill

logger = logging.getLogger(__name__)

class SkillMetricsTracker:
    """Updates skill execution metrics using incremental statistics."""
    
    def record_execution(self, skill: Skill, success: bool, duration: float) -> None:
        """Record a single execution outcome and update running metrics."""
        skill.execution_count += 1
        n = skill.execution_count
        
        # Incremental mean for success rate and duration
        success_val = 1.0 if success else 0.0
        skill.success_rate = ((skill.success_rate * (n - 1)) + success_val) / n
        skill.average_duration = ((skill.average_duration * (n - 1)) + duration) / n
        
        # Confidence scales with success rate and execution count (diminishing returns)
        base_conf = min(1.0, skill.success_rate * (1.0 - (0.5 / (n + 1))))
        skill.confidence = round(max(0.1, min(1.0, base_conf)), 4)
        skill.updated_at = time.time()
        
        logger.info("Updated metrics for skill %s: success=%.2f, conf=%.2f, count=%d", 
                    skill.id, skill.success_rate, skill.confidence, n)
