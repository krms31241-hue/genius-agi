"""Agent Registry: Thread-safe agent metadata, availability, and load tracking."""
import time
import threading
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgentStatus(str, Enum):
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    RESTARTING = "restarting"

@dataclass
class AgentInfo:
    id: str
    name: str
    capabilities: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.ACTIVE
    current_load: int = 0
    max_concurrent: int = 3
    last_heartbeat: float = field(default_factory=time.monotonic)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available(self, heartbeat_timeout: float = 30.0) -> bool:
        if self.status in (AgentStatus.OFFLINE, AgentStatus.RESTARTING):
            return False
        if time.monotonic() - self.last_heartbeat > heartbeat_timeout:
            return False
        return self.current_load < self.max_concurrent

class AgentRegistry:
    """Thread-safe registry for agent discovery, load balancing, and heartbeat tracking."""
    def __init__(self, heartbeat_timeout: float = 30.0):
        self.agents: Dict[str, AgentInfo] = {}
        self.lock = threading.RLock()
        self.heartbeat_timeout = heartbeat_timeout

    def register(self, agent: AgentInfo) -> bool:
        with self.lock:
            if agent.id in self.agents:
                logger.warning("Agent %s already registered. Updating.", agent.id)
            self.agents[agent.id] = agent
            logger.info("Agent registered: %s (%s)", agent.id, agent.name)
            return True

    def deregister(self, agent_id: str) -> bool:
        with self.lock:
            if agent_id in self.agents:
                del self.agents[agent_id]
                logger.info("Agent deregistered: %s", agent_id)
                return True
            return False

    def update_heartbeat(self, agent_id: str) -> bool:
        with self.lock:
            agent = self.agents.get(agent_id)
            if agent:
                agent.last_heartbeat = time.monotonic()
                return True
            return False

    def update_load(self, agent_id: str, delta: int) -> bool:
        with self.lock:
            agent = self.agents.get(agent_id)
            if agent:
                agent.current_load = max(0, agent.current_load + delta)
                agent.status = AgentStatus.BUSY if agent.current_load >= agent.max_concurrent else AgentStatus.ACTIVE
                return True
            return False

    def get_available(self, capability: str) -> Optional[str]:
        """Return least-loaded available agent supporting the capability."""
        with self.lock:
            candidates = [
                a for a in self.agents.values()
                if capability in a.capabilities and a.is_available(self.heartbeat_timeout)
            ]
            if not candidates:
                return None
            candidates.sort(key=lambda a: a.current_load / max(1, a.max_concurrent))
            return candidates[0].id

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        with self.lock:
            return self.agents.get(agent_id)

    def list_agents(self) -> List[AgentInfo]:
        with self.lock:
            return list(self.agents.values())

    def mark_offline(self, agent_id: str) -> bool:
        with self.lock:
            agent = self.agents.get(agent_id)
            if agent:
                agent.status = AgentStatus.OFFLINE
                return True
            return False
