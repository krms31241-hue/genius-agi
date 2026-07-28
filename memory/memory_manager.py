"""Unified API for the AGI Memory Core."""
import sqlite3
import threading
import os
import logging
from typing import Any, Dict, List, Optional
from .memory_index import MemoryIndex
from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory
from .semantic_memory import SemanticMemory
from .skill_memory import SkillMemory
from .memory_models import Experience, Fact, Skill

logger = logging.getLogger(__name__)

class MemoryManager:
    """Thread-safe, persistent, auto-initializing memory orchestrator.
    All subsystems must interact with memory exclusively through this manager."""
    def __init__(self, db_path: str = "memory_core.db"):
        self.db_path = os.path.abspath(db_path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")

        self.index = MemoryIndex(self.conn, self.lock)
        self.working = WorkingMemory(self.conn, self.lock)
        self.episodic = EpisodicMemory(self.conn, self.lock, self.index)
        self.semantic = SemanticMemory(self.conn, self.lock, self.index)
        self.skill = SkillMemory(self.conn, self.lock, self.index)
        logger.info("MemoryManager initialized at %s", self.db_path)

    def close(self):
        """Safely close database connection."""
        with self.lock:
            try:
                self.conn.close()
            except Exception as e:
                logger.error("MemoryManager close failed: %s", e)

    # Working Memory API
    def set_working(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        return self.working.set(key, value, ttl)

    def get_working(self, key: str) -> Optional[Any]:
        return self.working.get(key)

    def update_working(self, key: str, value: Any) -> bool:
        return self.working.update(key, value)

    def clear_working(self) -> bool:
        return self.working.clear()

    # Episodic Memory API
    def add_experience(self, experience: Experience) -> bool:
        return self.episodic.add(experience)

    def search_experiences(self, goal: Optional[str] = None, success: Optional[bool] = None, limit: int = 10) -> List[Experience]:
        return self.episodic.search(goal, success, limit)

    def recent_experiences(self, limit: int = 10) -> List[Experience]:
        return self.episodic.recent(limit)

    def get_episodic_stats(self) -> Dict[str, Any]:
        return self.episodic.statistics()

    # Semantic Memory API
    def add_fact(self, fact: Fact) -> bool:
        return self.semantic.add_fact(fact)

    def update_fact(self, fact_id: str, content: Optional[str] = None, confidence: Optional[float] = None) -> bool:
        return self.semantic.update_fact(fact_id, content, confidence)

    def delete_fact(self, fact_id: str) -> bool:
        return self.semantic.delete_fact(fact_id)

    def search_facts(self, query: str, tags: Optional[List[str]] = None) -> List[Fact]:
        return self.semantic.search(query, tags)

    # Skill Memory API
    def learn_skill(self, skill: Skill) -> bool:
        return self.skill.learn_skill(skill)

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.skill.get_skill(name)

    def update_skill(self, name: str, success_rate: Optional[float] = None, times_used: Optional[int] = None) -> bool:
        return self.skill.update_skill(name, success_rate, times_used)

    def list_skills(self) -> List[Skill]:
        return self.skill.list_skills()

    # Global Index API
    def search_index(self, query: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        return self.index.search(query, entity_type)
