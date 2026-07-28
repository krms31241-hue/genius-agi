"""Stores experiences and past actions."""
import sqlite3
import threading
import json
import logging
from typing import List, Dict, Any, Optional
from .memory_models import Experience

logger = logging.getLogger(__name__)

class EpisodicMemory:
    """Persistent storage for AGI experiences and execution history."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock, index: Any):
        self.conn = conn
        self.lock = lock
        self.index = index
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    goal TEXT,
                    action TEXT,
                    result TEXT,
                    success INTEGER,
                    duration REAL,
                    metadata TEXT
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_timestamp ON episodic_memory(timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ep_goal ON episodic_memory(goal)")
            self.conn.commit()

    def add(self, experience: Experience) -> bool:
        with self.lock:
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO episodic_memory (id, timestamp, goal, action, result, success, duration, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (experience.id, experience.timestamp, experience.goal, experience.action,
                      experience.result, int(experience.success), experience.duration, json.dumps(experience.metadata)))
                self.conn.commit()
                self.index.index_entity("episodic", experience.id, tags=[], keywords=[experience.action, experience.result],
                                        goal=experience.goal, timestamp=experience.timestamp)
                return True
            except Exception as e:
                logger.error("EpisodicMemory add failed: %s", e)
                return False

    def search(self, goal: Optional[str] = None, success: Optional[bool] = None, limit: int = 10) -> List[Experience]:
        with self.lock:
            try:
                sql = "SELECT id, timestamp, goal, action, result, success, duration, metadata FROM episodic_memory WHERE 1=1"
                params = []
                if goal:
                    sql += " AND goal LIKE ?"
                    params.append(f"%{goal}%")
                if success is not None:
                    sql += " AND success=?"
                    params.append(int(success))
                sql += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                cur = self.conn.execute(sql, params)
                return [Experience.from_dict({
                    "id": r[0], "timestamp": r[1], "goal": r[2], "action": r[3],
                    "result": r[4], "success": bool(r[5]), "duration": r[6],
                    "metadata": json.loads(r[7]) if r[7] else {}
                }) for r in cur.fetchall()]
            except Exception as e:
                logger.error("EpisodicMemory search failed: %s", e)
                return []

    def recent(self, limit: int = 10) -> List[Experience]:
        return self.search(limit=limit)

    def statistics(self) -> Dict[str, Any]:
        with self.lock:
            try:
                total = self.conn.execute("SELECT COUNT(*) FROM episodic_memory").fetchone()[0]
                success = self.conn.execute("SELECT COUNT(*) FROM episodic_memory WHERE success=1").fetchone()[0]
                avg_dur = self.conn.execute("SELECT AVG(duration) FROM episodic_memory").fetchone()[0] or 0.0
                return {"total_experiences": total, "successful": success, "failed": total - success, "avg_duration": round(avg_dur, 3)}
            except Exception as e:
                logger.error("EpisodicMemory stats failed: %s", e)
                return {}
