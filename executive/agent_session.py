"""Agent Session: Tracks execution state, heartbeats, timeouts, and results."""
import time
import threading
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

@dataclass
class AgentSession:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    task_id: str = ""
    status: SessionStatus = SessionStatus.PENDING
    started_at: float = 0.0
    last_heartbeat: float = 0.0
    completed_at: float = 0.0
    result: Any = None
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class SessionManager:
    """Thread-safe session lifecycle management."""
    def __init__(self):
        self.sessions: Dict[str, AgentSession] = {}
        self.lock = threading.RLock()

    def create(self, agent_id: str, task_id: str, metadata: Dict[str, Any] = None) -> AgentSession:
        with self.lock:
            session = AgentSession(
                agent_id=agent_id,
                task_id=task_id,
                status=SessionStatus.PENDING,
                metadata=metadata or {}
            )
            self.sessions[session.session_id] = session
            return session

    def start(self, session_id: str) -> bool:
        with self.lock:
            s = self.sessions.get(session_id)
            if s and s.status == SessionStatus.PENDING:
                s.status = SessionStatus.RUNNING
                s.started_at = time.monotonic()
                s.last_heartbeat = time.monotonic()
                return True
            return False

    def heartbeat(self, session_id: str) -> bool:
        with self.lock:
            s = self.sessions.get(session_id)
            if s and s.status == SessionStatus.RUNNING:
                s.last_heartbeat = time.monotonic()
                return True
            return False

    def complete(self, session_id: str, result: Any) -> bool:
        with self.lock:
            s = self.sessions.get(session_id)
            if s and s.status == SessionStatus.RUNNING:
                s.status = SessionStatus.COMPLETED
                s.result = result
                s.completed_at = time.monotonic()
                return True
            return False

    def fail(self, session_id: str, error: str) -> bool:
        with self.lock:
            s = self.sessions.get(session_id)
            if s and s.status == SessionStatus.RUNNING:
                s.status = SessionStatus.FAILED
                s.error = error
                s.completed_at = time.monotonic()
                return True
            return False

    def timeout(self, session_id: str) -> bool:
        with self.lock:
            s = self.sessions.get(session_id)
            if s and s.status == SessionStatus.RUNNING:
                s.status = SessionStatus.TIMEOUT
                s.error = "Execution exceeded timeout"
                s.completed_at = time.monotonic()
                return True
            return False

    def get(self, session_id: str) -> Optional[AgentSession]:
        with self.lock:
            return self.sessions.get(session_id)

    def get_active(self) -> List[AgentSession]:
        with self.lock:
            return [s for s in self.sessions.values() if s.status == SessionStatus.RUNNING]

    def get_by_task(self, task_id: str) -> Optional[AgentSession]:
        with self.lock:
            for s in self.sessions.values():
                if s.task_id == task_id:
                    return s
            return None
