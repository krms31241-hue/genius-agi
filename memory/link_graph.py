"""Cross Memory Linking Graph."""
import sqlite3
import threading
import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger(__name__)

class MemoryGraph:
    """Stores and queries relationships between memories."""
    
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self.conn = conn
        self.lock = lock
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_links (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    PRIMARY KEY (source_id, target_id, relation)
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_link_src ON memory_links(source_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_link_tgt ON memory_links(target_id)")
            self.conn.commit()

    def add_link(self, source: str, target: str, relation: str = "related", weight: float = 1.0) -> bool:
        with self.lock:
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO memory_links (source_id, target_id, relation, weight)
                    VALUES (?, ?, ?, ?)
                """, (source, target, relation, weight))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("Add link failed: %s", e)
                return False

    def remove_link(self, source: str, target: str, relation: str = None) -> bool:
        with self.lock:
            try:
                if relation:
                    self.conn.execute("DELETE FROM memory_links WHERE source_id=? AND target_id=? AND relation=?", (source, target, relation))
                else:
                    self.conn.execute("DELETE FROM memory_links WHERE source_id=? AND target_id=?", (source, target))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("Remove link failed: %s", e)
                return False

    def related(self, memory_id: str, relation: str = None) -> List[Dict[str, Any]]:
        """Find directly linked memories."""
        with self.lock:
            try:
                if relation:
                    cur = self.conn.execute("""
                        SELECT target_id, relation, weight FROM memory_links WHERE source_id=? AND relation=?
                        UNION
                        SELECT source_id, relation, weight FROM memory_links WHERE target_id=? AND relation=?
                    """, (memory_id, relation, memory_id, relation))
                else:
                    cur = self.conn.execute("""
                        SELECT target_id, relation, weight FROM memory_links WHERE source_id=?
                        UNION
                        SELECT source_id, relation, weight FROM memory_links WHERE target_id=?
                    """, (memory_id, memory_id))
                return [{"id": r[0], "relation": r[1], "weight": r[2]} for r in cur.fetchall()]
            except Exception as e:
                logger.error("Related query failed: %s", e)
                return []

    def neighbors(self, memory_id: str) -> List[str]:
        """Return IDs of all connected neighbors."""
        return [r["id"] for r in self.related(memory_id)]

    def connected_component(self, memory_id: str, max_depth: int = 3) -> Set[str]:
        """BFS to find all transitively connected memories."""
        visited = set()
        queue = [(memory_id, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for nid in self.neighbors(current):
                if nid not in visited:
                    queue.append((nid, depth + 1))
        visited.discard(memory_id)
        return visited
