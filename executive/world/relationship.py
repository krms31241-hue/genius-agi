"""Relationship Manager: Defines and validates named relationship types for the Knowledge Graph."""
from enum import Enum
from typing import Dict, Any, Set

class RelationshipType(str, Enum):
    """Standard relationship types for world entity connections."""
    DEPENDS_ON = "depends_on"
    OWNS = "owns"
    CREATED_BY = "created_by"
    CONTROLS = "controls"
    COMMUNICATES_WITH = "communicates_with"
    CONTAINS = "contains"
    PART_OF = "part_of"
    BLOCKS = "blocks"
    USES = "uses"
    RELATED_TO = "related_to"

class RelationshipManager:
    """Manages allowed relationship types and their metadata."""
    def __init__(self) -> None:
        self.allowed_types: Set[str] = set(RelationshipType)
        self.type_metadata: Dict[str, Dict[str, Any]] = {}

    def register_type(self, rel_type: str, metadata: Dict[str, Any] = None) -> None:
        """Register a custom relationship type."""
        self.allowed_types.add(rel_type)
        self.type_metadata[rel_type] = metadata or {}

    def is_valid_type(self, rel_type: str) -> bool:
        """Check if a relationship type is registered."""
        return rel_type in self.allowed_types

    def get_metadata(self, rel_type: str) -> Dict[str, Any]:
        """Retrieve metadata for a relationship type."""
        return self.type_metadata.get(rel_type, {})
