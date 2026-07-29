"""Data models for causal reasoning, chains, and results."""
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List

class CausalType(str, Enum):
    """Standard causal relationship types."""
    CAUSES = "causes"
    PREVENTS = "prevents"
    ENABLES = "enables"
    CORRELATES = "correlates"
    DEPENDS_ON = "depends_on"

@dataclass
class CausalRelation:
    """Represents a directed causal link between two entities."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    cause_id: str = ""
    effect_id: str = ""
    relation_type: str = CausalType.CAUSES
    confidence: float = 1.0
    evidence: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CausalRelation":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class CausalChain:
    """Sequence of causal relations linking a root cause to a final effect."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    nodes: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    root_cause_id: str = ""
    final_effect_id: str = ""
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ReasoningResult:
    """Structured output from reasoning queries."""
    query: str = ""
    explanation: str = ""
    causes: List[Dict[str, Any]] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    chains: List[CausalChain] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["chains"] = [c.to_dict() for c in self.chains]
        return d
