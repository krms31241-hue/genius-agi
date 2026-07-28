"""Data models for Decision Core."""
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class Candidate:
    """Represents a potential decision or action path."""
    id: str
    action: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Decision:
    """Final evaluated decision object."""
    decision: str
    score: float
    confidence: float
    uncertainty: float
    risk: float
    reason: List[str]
    alternatives: List[Candidate]
    metadata: Dict[str, Any] = field(default_factory=dict)
