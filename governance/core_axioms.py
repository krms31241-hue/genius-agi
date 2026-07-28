"""Core Axioms: Immutable foundational principles for self-governance."""
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

@dataclass
class CoreAxiom:
    id: str
    title: str
    description: str
    priority: int = 1
    immutable: bool = True
    enabled: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoreAxiom":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

DEFAULT_AXIOMS: List[CoreAxiom] = [
    CoreAxiom(id="axiom_knowledge", title="Preserve Knowledge", description="Never delete or corrupt learned information without explicit migration.", priority=10),
    CoreAxiom(id="axiom_stability", title="Preserve Stability", description="System state must remain operable. No unrecoverable transitions.", priority=9),
    CoreAxiom(id="axiom_tests", title="Never Decrease Test Success", description="Test pass rate must never drop below baseline after any evolution step.", priority=8),
    CoreAxiom(id="axiom_rollback", title="Always Support Rollback", description="Every state change must be reversible to a known good snapshot.", priority=7),
    CoreAxiom(id="axiom_capability", title="Improve Long-Term Capability", description="Evolution must yield net positive capability gain over time.", priority=6)
]
