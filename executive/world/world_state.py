"""In-memory manager for current world entities and event history."""
import copy
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from .models import WorldEntity, WorldEvent

logger = logging.getLogger(__name__)

class WorldState:
    """Thread-aware in-memory store for entities and events.
    Provides CRUD operations, filtering, and state export/import."""
    
    def __init__(self) -> None:
        self.entities: Dict[str, WorldEntity] = {}
        self.events: List[WorldEvent] = []

    def add_entity(self, entity: WorldEntity) -> bool:
        """Register a new entity. Returns False if ID already exists."""
        if entity.id in self.entities:
            logger.warning("Entity %s already exists.", entity.id)
            return False
        self.entities[entity.id] = entity
        return True

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Optional[WorldEntity]:
        """Apply partial updates to an entity's attributes, relationships, or metadata."""
        entity = self.entities.get(entity_id)
        if not entity:
            return None
        if "attributes" in updates:
            entity.attributes.update(updates["attributes"])
        if "relationships" in updates:
            entity.relationships.update(updates["relationships"])
        if "metadata" in updates:
            entity.metadata.update(updates["metadata"])
        if "entity_type" in updates:
            entity.entity_type = updates["entity_type"]
        entity.updated_at = time.time()
        return entity

    def delete_entity(self, entity_id: str) -> bool:
        """Remove an entity from the current state."""
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        """Retrieve an entity by ID."""
        return self.entities.get(entity_id)

    def query_entities(self, filter_fn: Callable[[WorldEntity], bool]) -> List[WorldEntity]:
        """Return all entities matching the predicate function."""
        return [e for e in self.entities.values() if filter_fn(e)]

    def add_event(self, event: WorldEvent) -> None:
        """Append a state change event to the history log."""
        self.events.append(event)

    def get_events(self, entity_id: Optional[str] = None) -> List[WorldEvent]:
        """Retrieve event history, optionally filtered by entity ID."""
        if entity_id:
            return [e for e in self.events if e.entity_id == entity_id]
        return list(self.events)

    def export_state(self) -> Dict[str, Any]:
        """Serialize current state and events for persistence."""
        return {
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "events": [e.to_dict() for e in self.events]
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Restore state and events from serialized data."""
        self.entities = {eid: WorldEntity.from_dict(d) for eid, d in state.get("entities", {}).items()}
        self.events = [WorldEvent.from_dict(d) for d in state.get("events", [])]
