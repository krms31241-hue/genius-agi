"""Skill Library: Persistent storage, lifecycle management, and metrics orchestration."""
import os
import json
import time
import tempfile
import shutil
import logging
from typing import Dict, Any, List, Optional
from .skill import Skill
from .skill_registry import SkillRegistry
from .skill_metrics import SkillMetricsTracker

logger = logging.getLogger(__name__)

class SkillLibrary:
    """Production-grade skill persistence and management layer."""
    
    def __init__(self, data_dir: str = "learning_data") -> None:
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "skills.json")
        self.registry = SkillRegistry()
        self.metrics = SkillMetricsTracker()
        self._load()

    def add_skill(self, skill: Skill) -> bool:
        if self.registry.register(skill):
            self._save()
            return True
        return False

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.registry.get(skill_id)

    def update_skill(self, skill: Skill) -> bool:
        if skill.id not in self.registry.skills:
            return False
        self.registry.skills[skill.id] = skill
        self._save()
        return True

    def retire_skill(self, skill_id: str, reason: str = "deprecated") -> bool:
        skill = self.registry.get(skill_id)
        if not skill:
            return False
        skill.status = "retired"
        skill.metadata["retirement_reason"] = reason
        skill.updated_at = time.time()
        self._save()
        logger.info("Skill %s retired: %s", skill_id, reason)
        return True

    def search(self, query: str = "", category: str = "", tags: Optional[List[str]] = None) -> List[Skill]:
        return self.registry.search(query, category, tags)

    def record_execution(self, skill_id: str, success: bool, duration: float) -> bool:
        skill = self.registry.get(skill_id)
        if not skill or skill.status != "active":
            return False
        self.metrics.record_execution(skill, success, duration)
        self._save()
        return True

    def _save(self) -> None:
        data = {"skills": [s.to_dict() for s in self.registry.skills.values()]}
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, self.store_path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _load(self) -> None:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                for sd in data.get("skills", []):
                    skill = Skill.from_dict(sd)
                    self.registry.register(skill)
            except Exception as e:
                logger.error("Failed to load skill library: %s", e)
