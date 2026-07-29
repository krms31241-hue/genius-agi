"""World Model Orchestrator: Manages state, events, snapshots, rollback, and persistence."""
import os
import json
import time
import copy
import tempfile
import shutil
import logging
import uuid
from typing import Dict, Any, List, Optional, Callable
from .models import WorldEntity, WorldEvent, WorldSnapshot
from .world_state import WorldState

logger = logging.getLogger(__name__)

class WorldModel:
    """Production-grade world model supporting entity lifecycle, event sourcing,
    immutable snapshots, deterministic rollback, and atomic persistence."""
    
    def __init__(self, data_dir: str = "executive_data") -> None:
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_path = os.path.join(self.data_dir, "world_state.json")
        self.snapshots_dir = os.path.join(self.data_dir, "world_snapshots")
        os.makedirs(self.snapshots_dir, exist_ok=True)

        self.state = WorldState()
        self.snapshots: Dict[str, WorldSnapshot] = {}
        self._load_state()

    def create_entity(self, entity_type: str, attributes: Dict[str, Any] = None,
                      relationships: Dict[str, List[str]] = None, metadata: Dict[str, Any] = None) -> WorldEntity:
        """Create and register a new entity. Automatically records creation event."""
        entity = WorldEntity(
            entity_type=entity_type,
            attributes=attributes or {},
            relationships=relationships or {},
            metadata=metadata or {}
        )
        self.state.add_entity(entity)
        self._record_event(entity.id, {}, entity.to_dict(), "system", "entity_created")
        logger.info("Created entity %s of type %s", entity.id, entity_type)
        return entity

    def update_entity(self, entity_id: str, updates: Dict[str, Any], source: str = "system", reason: str = "update") -> Optional[WorldEntity]:
        """Update an entity and record before/after state in event history."""
        entity = self.state.get_entity(entity_id)
        if not entity:
            return None
        before = copy.deepcopy(entity.to_dict())
        updated = self.state.update_entity(entity_id, updates)
        if updated:
            after = copy.deepcopy(updated.to_dict())
            self._record_event(entity_id, before, after, source, reason)
        return updated

    def delete_entity(self, entity_id: str, source: str = "system", reason: str = "deletion") -> bool:
        """Delete an entity and record removal event."""
        entity = self.state.get_entity(entity_id)
        if not entity:
            return False
        before = copy.deepcopy(entity.to_dict())
        success = self.state.delete_entity(entity_id)
        if success:
            self._record_event(entity_id, before, {}, source, reason)
        return success

    def get_entity(self, entity_id: str) -> Optional[WorldEntity]:
        """Retrieve current entity state."""
        return self.state.get_entity(entity_id)

    def query_entities(self, filter_fn: Callable[[WorldEntity], bool]) -> List[WorldEntity]:
        """Query entities using a predicate function."""
        return self.state.query_entities(filter_fn)

    def get_history(self, entity_id: Optional[str] = None) -> List[WorldEvent]:
        """Retrieve event history, optionally scoped to an entity."""
        return self.state.get_events(entity_id)

    def create_snapshot(self, metadata: Dict[str, Any] = None) -> WorldSnapshot:
        """Capture an immutable point-in-time snapshot of the world state."""
        snap_id = uuid.uuid4().hex[:12]
        entities_copy = copy.deepcopy({eid: e.to_dict() for eid, e in self.state.entities.items()})
        snapshot = WorldSnapshot(
            id=snap_id,
            timestamp=time.time(),
            entities=entities_copy,
            event_count=len(self.state.events),
            metadata=metadata or {}
        )
        self.snapshots[snap_id] = snapshot
        self._save_snapshot(snapshot)
        logger.info("Created snapshot %s with %d entities", snap_id, len(entities_copy))
        return snapshot

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """Restore world state and truncate event history to a previous snapshot."""
        snapshot = self.snapshots.get(snapshot_id)
        if not snapshot:
            snapshot = self._load_snapshot(snapshot_id)
            if not snapshot:
                logger.warning("Snapshot %s not found", snapshot_id)
                return False

        self.state.entities = {eid: WorldEntity.from_dict(d) for eid, d in snapshot.entities.items()}
        self.state.events = self.state.events[:snapshot.event_count]
        logger.info("Rolled back to snapshot %s", snapshot_id)
        return True

    def save(self) -> None:
        """Atomically persist current world state to disk."""
        self._atomic_save(self.state_path, self.state.export_state())

    def load(self) -> None:
        """Reload world state from disk."""
        self._load_state()

    def _record_event(self, entity_id: str, before: Dict[str, Any], after: Dict[str, Any], source: str, reason: str) -> None:
        """Internal helper to create and store a world event."""
        event = WorldEvent(
            entity_id=entity_id,
            before_state=before,
            after_state=after,
            timestamp=time.time(),
            source=source,
            reason=reason
        )
        self.state.add_event(event)

    def _save_snapshot(self, snapshot: WorldSnapshot) -> None:
        """Persist snapshot to dedicated directory."""
        path = os.path.join(self.snapshots_dir, f"{snapshot.id}.json")
        self._atomic_save(path, snapshot.to_dict())

    def _load_snapshot(self, snapshot_id: str) -> Optional[WorldSnapshot]:
        """Load snapshot from disk if not in memory."""
        path = os.path.join(self.snapshots_dir, f"{snapshot_id}.json")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                snap = WorldSnapshot.from_dict(data)
                self.snapshots[snapshot_id] = snap
                return snap
            except Exception as e:
                logger.error("Failed to load snapshot %s: %s", snapshot_id, e)
        return None

    def _load_state(self) -> None:
        """Restore state from persistence layer."""
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    data = json.load(f)
                self.state.import_state(data)
                logger.info("World state loaded from disk")
            except Exception as e:
                logger.error("Failed to load world state: %s", e)

    def _atomic_save(self, path: str, data: Any) -> None:
        """Atomic file write using tempfile and move to prevent corruption."""
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
