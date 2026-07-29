"""Simulation Result: Structured prediction output."""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass
class SimulationResult:
    """Deterministic output from a simulation run."""
    success: bool
    predicted_changes: List[Dict[str, Any]]
    predicted_risks: List[Dict[str, Any]]
    confidence: float
    estimated_cost: float
    estimated_duration: float
    rollback_possible: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return asdict(self)
