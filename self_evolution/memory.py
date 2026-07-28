"""Persistent memory for learning and failure prevention."""
import sqlite3
import hashlib
import json
import time
from typing import Dict, Any, Optional, List
from .config import MEMORY_DB_PATH

class EvolutionMemory:
    def __init__(self, db_path: str = MEMORY_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_hash TEXT UNIQUE NOT NULL,
                    finding_type TEXT NOT NULL,
                    affected_files TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details TEXT,
                    timestamp REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS metrics (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_pattern ON attempts(pattern_hash);
                CREATE INDEX IF NOT EXISTS idx_outcome ON attempts(outcome);
            """)

    def _hash_pattern(self, finding_type: str, files: List[str], reason: str) -> str:
        raw = f"{finding_type}|{sorted(files)}|{reason}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def is_known_failure(self, finding_type: str, files: List[str], reason: str) -> bool:
        h = self._hash_pattern(finding_type, files, reason)
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT outcome FROM attempts WHERE pattern_hash=? AND outcome='failed'", (h,))
            return cur.fetchone() is not None

    def record_attempt(self, finding_type: str, files: List[str], reason: str, outcome: str, details: str = ""):
        h = self._hash_pattern(finding_type, files, reason)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO attempts (pattern_hash, finding_type, affected_files, outcome, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (h, finding_type, json.dumps(files), outcome, details, time.time()))

    def get_stats(self) -> Dict[str, int]:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
            failed = conn.execute("SELECT COUNT(*) FROM attempts WHERE outcome='failed'").fetchone()[0]
            return {"total_attempts": total, "failed_patterns": failed}

    def update_metric(self, key: str, value: Any):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO metrics (key, value, updated_at) VALUES (?, ?, ?)
            """, (key, json.dumps(value), time.time()))

    def get_metric(self, key: str, default: Any = None) -> Any:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM metrics WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else default
