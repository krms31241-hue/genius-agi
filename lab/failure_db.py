"""Failure storage, learning, and repetition prevention."""
import sqlite3
import hashlib
import json
import time
import threading
from typing import Dict, Any, Optional

class FailureDB:
    """Stores failures, learns patterns, prevents repetition. Adaptive blocking."""
    PERMANENT_CATEGORIES = {"security", "syntax", "circular_dependencies", "architecture"}
    TRANSIENT_CATEGORIES = {"sandbox", "runtime", "timeout", "performance", "memory", "test_failure"}

    def __init__(self, db_path: str = "lab_failures.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Idempotent initialization with safe schema migration."""
        with self.lock:
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_hash TEXT NOT NULL,
                    pattern_sig TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    details TEXT,
                    timestamp REAL NOT NULL,
                    blocked INTEGER DEFAULT 1
                );
                CREATE INDEX IF NOT EXISTS idx_hash ON failures(code_hash);
                CREATE INDEX IF NOT EXISTS idx_pattern ON failures(pattern_sig);
            """)
            try:
                self.conn.execute("ALTER TABLE failures ADD COLUMN category TEXT DEFAULT 'runtime'")
            except Exception:
                pass
            self.conn.commit()

    def _hash_code(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _extract_pattern(self, code: str, error: str) -> str:
        lines = [l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith("#")]
        sig = "|".join(lines[:10]) + "::" + error.split("\n")[0]
        return hashlib.md5(sig.encode()).hexdigest()

    def is_known_failure(self, code: str) -> Optional[Dict[str, Any]]:
        h = self._hash_code(code)
        with self.lock:
            cur = self.conn.execute(
                "SELECT error_type, details, timestamp, category FROM failures WHERE code_hash=? AND blocked=1 ORDER BY timestamp DESC LIMIT 1",
                (h,)
            )
            row = cur.fetchone()
            if row:
                return {"error_type": row[0], "details": row[1], "timestamp": row[2], "category": row[3]}
        return None

    def record_failure(self, code: str, error_type: str, details: str, category: str = "runtime"):
        h = self._hash_code(code)
        pat = self._extract_pattern(code, details)
        with self.lock:
            self.conn.execute(
                "INSERT INTO failures (code_hash, pattern_sig, error_type, category, details, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                (h, pat, error_type, category, details, time.time())
            )
            self.conn.commit()

    def learn_and_block(self, code: str, error_type: str, details: str, category: str = "runtime"):
        self.record_failure(code, error_type, details, category)
        return True

    def unblock_failure(self, code: str):
        """Adaptive forgetting: unblocks a hash after successful revalidation."""
        h = self._hash_code(code)
        with self.lock:
            self.conn.execute("UPDATE failures SET blocked=0 WHERE code_hash=?", (h,))
            self.conn.commit()

    def update_failure_status(self, code: str, blocked: bool):
        h = self._hash_code(code)
        with self.lock:
            self.conn.execute("UPDATE failures SET blocked=? WHERE code_hash=?", (1 if blocked else 0, h))
            self.conn.commit()

    def get_stats(self) -> Dict[str, int]:
        with self.lock:
            total = self.conn.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
            blocked = self.conn.execute("SELECT COUNT(*) FROM failures WHERE blocked=1").fetchone()[0]
            return {"total_failures": total, "blocked_patterns": blocked}

    def __del__(self):
        try:
            self.conn.close()
        except Exception:
            pass
