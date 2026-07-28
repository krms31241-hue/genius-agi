"""Data models for all memory entities."""
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List

@dataclass
class Experience:
    """Represents a past action or event."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    goal: str = ""
    action: str = ""
    result: str = ""
    success: bool = False
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Experience":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Fact:
    """Represents learned knowledge or semantic information."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    content: str = ""
    source: str = ""
    confidence: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tags"] = ",".join(self.tags)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fact":
        if isinstance(data.get("tags"), str):
            data["tags"] = [t.strip() for t in data["tags"].split(",") if t.strip()]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class Skill:
    """Represents a learned reusable capability."""
    name: str = ""
    description: str = ""
    input_schema: str = "{}"
    output_schema: str = "{}"
    example: str = ""
    success_rate: float = 0.0
    times_used: int = 0
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
