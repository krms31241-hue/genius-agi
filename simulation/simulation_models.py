"""Data models for simulation actions and plans."""
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

@dataclass
class SimulationAction:
    """Represents a single atomic operation to be simulated."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_entity_id: Optional[str] = None
    action_type: str = "update"  # create, update, delete, custom
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_cost: float = 1.0
    estimated_duration: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "target_entity_id": self.target_entity_id,
            "action_type": self.action_type, "parameters": self.parameters,
            "estimated_cost": self.estimated_cost, "estimated_duration": self.estimated_duration,
            "metadata": self.metadata
        }

@dataclass
class SimulationPlan:
    """Represents a sequence of actions to be simulated together."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    actions: List[SimulationAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata
        }
