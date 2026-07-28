"""Memory Statistics and Metrics Engine."""
import sqlite3
import threading
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MemoryStatistics:
    """Tracks and computes memory system metrics."""
    
    def __init__(self, conn: sqlite3.Connection, lock: threading.RLock):
        self.conn = conn
        self.lock = lock
        self._init_table()

    def _init_table(self):
        with self.lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_metrics (
                    key TEXT PRIMARY KEY,
                    value REAL DEFAULT 0.0,
                    updated_at REAL
                )
            """)
            self.conn.commit()

    def increment(self, key: str, amount: float = 1.0) -> bool:
        with self.lock:
            try:
                cur = self.conn.execute("SELECT value FROM memory_metrics WHERE key=?", (key,))
                row = cur.fetchone()
                new_val = (row[0] + amount) if row else amount
                self.conn.execute("""
                    INSERT OR REPLACE INTO memory_metrics (key, value, updated_at) VALUES (?, ?, ?)
                """, (key, new_val, time.time()))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error("Metric increment failed: %s", e)
                return False

    def get(self, key: str, default: float = 0.0) -> float:
        with self.lock:
            try:
                cur = self.conn.execute("SELECT value FROM memory_metrics WHERE key=?", (key,))
                row = cur.fetchone()
                return row[0] if row else default
            except Exception:
                return default

    def get_full_report(self, manager: Any) -> Dict[str, Any]:
        """Compute comprehensive memory statistics."""
        try:
            ep_stats = manager.get_episodic_stats()
            total_ep = ep_stats.get("total_experiences", 0)
            successful = ep_stats.get("successful", 0)
            
            promoted = self.get("promoted_count")
            forgotten = self.get("forgotten_count")
            replay_count = self.get("replay_count")
            compress_ops = self.get("compression_ops")
            
            success_rate = (successful / total_ep * 100) if total_ep > 0 else 0.0
            recall_rate = (replay_count / max(1, total_ep)) * 100
            
            return {
                "total_memories": total_ep,
                "promoted_memories": int(promoted),
                "forgotten_memories": int(forgotten),
                "compression_ratio": round(compress_ops / max(1, total_ep), 3),
                "replay_count": int(replay_count),
                "recall_rate": round(recall_rate, 2),
                "success_rate": round(success_rate, 2),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error("Statistics report failed: %s", e)
            return {}
