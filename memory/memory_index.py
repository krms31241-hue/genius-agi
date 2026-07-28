"""Fast lookup index for memory entities."""
import sqlite3
import threading
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MemoryIndex:
    """Indexes memory entities by tags, keywords, goals, and timestamps."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self.conn = conn
        self.lock = lock
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    tag TEXT,
                    keyword TEXT,
                    goal TEXT,
                    timestamp REAL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_entity ON memory_index(entity_type, entity_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tag ON memory_index(tag)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_keyword ON memory_index(keyword)")
            self.conn.commit()

    def index_entity(self, entity_type: str, entity_id: str, tags: List[str] = None,
                     keywords: List[str] = None, goal: str = None, timestamp: float = None):
        with self.lock:
            try:
                self.conn.execute("DELETE FROM memory_index WHERE entity_type=? AND entity_id=?", (entity_type, entity_id))
                ts = timestamp or 0.0
                for tag in (tags or []):
                    self.conn.execute("INSERT INTO memory_index (entity_type, entity_id, tag, goal, timestamp) VALUES (?, ?, ?, ?, ?)",
                                      (entity_type, entity_id, tag.lower(), goal, ts))
                for kw in (keywords or []):
                    self.conn.execute("INSERT INTO memory_index (entity_type, entity_id, keyword, goal, timestamp) VALUES (?, ?, ?, ?, ?)",
                                      (entity_type, entity_id, kw.lower(), goal, ts))
                if goal:
                    self.conn.execute("INSERT INTO memory_index (entity_type, entity_id, goal, timestamp) VALUES (?, ?, ?, ?)",
                                      (entity_type, entity_id, goal, ts))
                self.conn.commit()
            except Exception as e:
                logger.error("Indexing failed: %s", e)

    def search(self, query: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        q = f"%{query.lower()}%"
        with self.lock:
            try:
                sql = "SELECT entity_type, entity_id, tag, keyword, goal, timestamp FROM memory_index WHERE (tag LIKE ? OR keyword LIKE ? OR goal LIKE ?)"
                params = [q, q, q]
                if entity_type:
                    sql += " AND entity_type=?"
                    params.append(entity_type)
                sql += " ORDER BY timestamp DESC"
                cur = self.conn.execute(sql, params)
                return [{"entity_type": r[0], "entity_id": r[1], "tag": r[2], "keyword": r[3], "goal": r[4], "timestamp": r[5]} for r in cur.fetchall()]
            except Exception as e:
                logger.error("Index search failed: %s", e)
                return []

    def remove_index(self, entity_type: str, entity_id: str):
        with self.lock:
            try:
                self.conn.execute("DELETE FROM memory_index WHERE entity_type=? AND entity_id=?", (entity_type, entity_id))
                self.conn.commit()
            except Exception as e:
                logger.error("Index removal failed: %s", e)
