from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ToolMetadata:
    """Immutable metadata definition for a registered tool."""
    name: str
    version: str
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    required_permissions: List[str] = field(default_factory=list)
    input_schema: Dict[str, object] = field(default_factory=dict)
    output_schema: Dict[str, object] = field(default_factory=dict)
