"""Stores learned facts and knowledge."""
import sqlite3
import threading
import time
import logging
from typing import List, Dict, Any, Optional
from .memory_models import Fact

logger = logging.getLogger(__name__)

class SemanticMemory:
    """Persistent storage for verified facts and conceptual knowledge."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock, index: Any):
        self.conn = conn
        self.lock = lock
        self.index = index
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT,
                    confidence REAL DEFAULT 0.5,
                    tags TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_title ON semantic_memory(title)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_sem_tags ON semantic_memory(tags)")
            self.conn.commit()

    def add_fact(self, fact: Fact) -> bool:
        with self.lock:
            try:
                d = fact.to_dict()
                self.conn.execute("""
                    INSERT OR REPLACE INTO semantic_memory (id, title, content, source, confidence, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (d["id"], d["title"], d["content"], d["source"], d["confidence"], d["tags"], d["created_at"], d["updated_at"]))
                self.conn.commit()
                self.index.index_entity("semantic", fact.id, tags=fact.tags, keywords=[fact.title, fact.content[:50]], timestamp=fact.updated_at)
                return True
            except Exception as e:
                logger.error("SemanticMemory add_fact failed: %s", e)
                return False

    def update_fact(self, fact_id: str, content: Optional[str] = None, confidence: Optional[float] = None) -> bool:
        with self.lock:
            try:
                updates = []
                params = []
                if content is not None:
                    updates.append("content=?")
                    params.append(content)
                if confidence is not None:
                    updates.append("confidence=?")
                    params.append(confidence)
                if not updates:
                    return False
                updates.append("updated_at=?")
                params.append(time.time())
                params.append(fact_id)
                self.conn.execute(f"UPDATE semantic_memory SET {', '.join(updates)} WHERE id=?", params)
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("SemanticMemory update_fact failed: %s", e)
                return False

    def delete_fact(self, fact_id: str) -> bool:
        with self.lock:
            try:
                self.conn.execute("DELETE FROM semantic_memory WHERE id=?", (fact_id,))
                self.conn.commit()
                self.index.remove_index("semantic", fact_id)
                return True
            except Exception as e:
                logger.error("SemanticMemory delete_fact failed: %s", e)
                return False

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[Fact]:
        with self.lock:
            try:
                sql = "SELECT id, title, content, source, confidence, tags, created_at, updated_at FROM semantic_memory WHERE (title LIKE ? OR content LIKE ?)"
                params = [f"%{query}%", f"%{query}%"]
                if tags:
                    tag_conditions = " OR ".join(["tags LIKE ?" for _ in tags])
                    sql += f" AND ({tag_conditions})"
                    params.extend([f"%{t}%" for t in tags])
                sql += " ORDER BY confidence DESC, updated_at DESC"
                cur = self.conn.execute(sql, params)
                return [Fact.from_dict({
                    "id": r[0], "title": r[1], "content": r[2], "source": r[3],
                    "confidence": r[4], "tags": r[5], "created_at": r[6], "updated_at": r[7]
                }) for r in cur.fetchall()]
            except Exception as e:
                logger.error("SemanticMemory search failed: %s", e)
                return []
