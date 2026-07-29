"""Skill Extractor: Learns reusable skills from successful execution telemetry."""
import logging
import hashlib
import time
from typing import Dict, Any, Optional
from .skill import Skill
from .skill_library import SkillLibrary

logger = logging.getLogger(__name__)

class SkillExtractor:
    """Analyzes execution outcomes and promotes successful patterns to reusable skills."""
    
    def __init__(self, library: SkillLibrary, min_success_rate: float = 0.8, min_executions: int = 3) -> None:
        self.library = library
        self.min_success_rate = min_success_rate
        self.min_executions = min_executions

    def extract_from_execution(self, execution_data: Dict[str, Any]) -> Optional[Skill]:
        """Generate a new skill if execution succeeded and pattern is novel."""
        if not execution_data.get("success"):
            return None
        action = execution_data.get("action", "")
        if not action:
            return None

        # Prevent duplicate extraction
        if self.library.search(query=action):
            return None

        sid = hashlib.sha256(f"skill_{action}_{time.time()}".encode()).hexdigest()[:12]
        skill = Skill(
            id=sid,
            name=action,
            description=execution_data.get("description", f"Learned from {action}"),
            category=execution_data.get("category", "learned"),
            tags=execution_data.get("tags", []),
            dependencies=execution_data.get("dependencies", []),
            metadata={"source": "execution_extractor", "raw_data": execution_data.get("metadata", {})},
            success_rate=1.0,
            execution_count=1,
            average_duration=execution_data.get("duration", 1.0),
            confidence=0.6
        )
        if self.library.add_skill(skill):
            logger.info("Extracted new skill: %s (%s)", skill.id, skill.name)
            return skill
        return None

    def promote_to_stable(self, skill_id: str) -> bool:
        """Promote a skill to stable status if it meets success/count thresholds."""
        skill = self.library.get_skill(skill_id)
        if not skill:
            return False
        if skill.execution_count >= self.min_executions and skill.success_rate >= self.min_success_rate:
            skill.confidence = min(1.0, skill.confidence + 0.2)
            skill.metadata["promoted"] = True
            skill.updated_at = time.time()
            self.library.update_skill(skill)
            logger.info("Skill %s promoted to stable", skill_id)
            return True
        return False
