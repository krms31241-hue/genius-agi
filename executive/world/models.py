"""Core data models for the World Model."""
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List

@dataclass
class WorldEntity:
    """Generic entity representing an object in the world state.
    
    Attributes:
        id: Unique identifier for the entity.
        entity_type: Categorization label (e.g., 'server', 'agent', 'resource').
        attributes: Key-value state data.
        relationships: Mapping of relation types to lists of target entity IDs.
        metadata: Auxiliary information (tags, ownership, etc.).
        created_at: Unix timestamp of creation.
        updated_at: Unix timestamp of last modification.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_type: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize entity to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldEntity":
        """Deserialize entity from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class WorldEvent:
    """Immutable record of a state transition for an entity.
    
    Attributes:
        id: Unique event identifier.
        entity_id: ID of the affected entity.
        before_state: Entity state prior to the change.
        after_state: Entity state after the change.
        timestamp: Unix timestamp of the event.
        source: Originator of the change (e.g., 'system', 'agent_1').
        reason: Human-readable explanation for the change.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_id: str = ""
    before_state: Dict[str, Any] = field(default_factory=dict)
    after_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldEvent":
        """Deserialize event from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class WorldSnapshot:
    """Point-in-time capture of the entire world state.
    Treated as immutable after creation. Deep copies are used to guarantee isolation.
    
    Attributes:
        id: Unique snapshot identifier.
        timestamp: Unix timestamp of capture.
        entities: Dictionary mapping entity IDs to their serialized state.
        event_count: Total number of events recorded at snapshot time.
        metadata: Snapshot annotations (e.g., 'pre_migration', 'checkpoint_1').
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    entities: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    event_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize snapshot to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldSnapshot":
        """Deserialize snapshot from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
