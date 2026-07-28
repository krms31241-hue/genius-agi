"""Temporary storage for current task, reasoning state, and active goals."""
import sqlite3
import threading
import time
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

class WorkingMemory:
    """Volatile storage with TTL support and automatic expiration."""
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self.conn = conn
        self.lock = lock
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS working_memory (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    expires_at REAL
                )
            """)
            self.conn.commit()

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        expires = (time.time() + ttl) if ttl else None
        with self.lock:
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO working_memory (key, value, expires_at) VALUES (?, ?, ?)
                """, (key, json.dumps(value), expires))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("WorkingMemory set failed: %s", e)
                return False

    def get(self, key: str) -> Optional[Any]:
        self.cleanup_expired()
        with self.lock:
            try:
                cur = self.conn.execute("SELECT value, expires_at FROM working_memory WHERE key=?", (key,))
                row = cur.fetchone()
                if row:
                    if row[1] and row[1] < time.time():
                        return None
                    return json.loads(row[0])
                return None
            except Exception as e:
                logger.error("WorkingMemory get failed: %s", e)
                return None

    def update(self, key: str, value: Any) -> bool:
        return self.set(key, value)

    def clear(self) -> bool:
        with self.lock:
            try:
                self.conn.execute("DELETE FROM working_memory")
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("WorkingMemory clear failed: %s", e)
                return False

    def cleanup_expired(self):
        with self.lock:
            try:
                self.conn.execute("DELETE FROM working_memory WHERE expires_at IS NOT NULL AND expires_at < ?", (time.time(),))
                self.conn.commit()
            except Exception as e:
                logger.error("WorkingMemory cleanup failed: %s", e)
