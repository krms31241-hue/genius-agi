"""Skill Data Model: Represents a learned, versioned, and tracked executable capability."""
import time
import uuid
import hashlib
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass
class Skill:
    """Immutable-core skill representation with mutable execution metrics."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    version: str = "1.0.0"
    description: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    success_rate: float = 0.0
    execution_count: int = 0
    average_duration: float = 0.0
    confidence: float = 0.5
    status: str = "active"  # active, retired, deprecated
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def content_hash(self) -> str:
        """Deterministic hash for duplicate detection based on semantic identity."""
        payload = f"{self.name}|{self.description}|{sorted(self.tags)}|{self.category}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize skill to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Deserialize skill from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
