"""Stores learned reusable skills."""
import sqlite3
import threading
import time
import logging
from typing import List, Dict, Any, Optional
from .memory_models import Skill

logger = logging.getLogger(__name__)

class SkillMemory:
    """Persistent storage for executable capabilities and learned procedures."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock, index: Any):
        self.conn = conn
        self.lock = lock
        self.index = index
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_memory (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    input_schema TEXT,
                    output_schema TEXT,
                    example TEXT,
                    success_rate REAL DEFAULT 0.0,
                    times_used INTEGER DEFAULT 0,
                    updated_at REAL
                )
            """)
            self.conn.commit()

    def learn_skill(self, skill: Skill) -> bool:
        with self.lock:
            try:
                d = skill.to_dict()
                self.conn.execute("""
                    INSERT OR REPLACE INTO skill_memory (name, description, input_schema, output_schema, example, success_rate, times_used, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (d["name"], d["description"], d["input_schema"], d["output_schema"], d["example"], d["success_rate"], d["times_used"], d["updated_at"]))
                self.conn.commit()
                self.index.index_entity("skill", skill.name, tags=[], keywords=[skill.name, skill.description], timestamp=skill.updated_at)
                return True
            except Exception as e:
                logger.error("SkillMemory learn_skill failed: %s", e)
                return False

    def get_skill(self, name: str) -> Optional[Skill]:
        with self.lock:
            try:
                cur = self.conn.execute("SELECT name, description, input_schema, output_schema, example, success_rate, times_used, updated_at FROM skill_memory WHERE name=?", (name,))
                row = cur.fetchone()
                if row:
                    return Skill.from_dict({
                        "name": row[0], "description": row[1], "input_schema": row[2],
                        "output_schema": row[3], "example": row[4], "success_rate": row[5],
                        "times_used": row[6], "updated_at": row[7]
                    })
                return None
            except Exception as e:
                logger.error("SkillMemory get_skill failed: %s", e)
                return None

    def update_skill(self, name: str, success_rate: Optional[float] = None, times_used: Optional[int] = None) -> bool:
        with self.lock:
            try:
                updates = []
                params = []
                if success_rate is not None:
                    updates.append("success_rate=?")
                    params.append(success_rate)
                if times_used is not None:
                    updates.append("times_used=?")
                    params.append(times_used)
                if not updates:
                    return False
                updates.append("updated_at=?")
                params.append(time.time())
                params.append(name)
                self.conn.execute(f"UPDATE skill_memory SET {', '.join(updates)} WHERE name=?", params)
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("SkillMemory update_skill failed: %s", e)
                return False

    def list_skills(self) -> List[Skill]:
        with self.lock:
            try:
                cur = self.conn.execute("SELECT name, description, input_schema, output_schema, example, success_rate, times_used, updated_at FROM skill_memory ORDER BY success_rate DESC")
                return [Skill.from_dict({
                    "name": r[0], "description": r[1], "input_schema": r[2],
                    "output_schema": r[3], "example": r[4], "success_rate": r[5],
                    "times_used": r[6], "updated_at": r[7]
                }) for r in cur.fetchall()]
            except Exception as e:
                logger.error("SkillMemory list_skills failed: %s", e)
                return []
