"""Experience Data Model: Represents a single execution step for replay learning."""
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any

@dataclass
class Experience:
    """Immutable-core experience representation with mutable priority."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    episode_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    action: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    success: bool = True
    reward: float = 0.0
    priority: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize experience to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experience":
        """Deserialize experience from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
