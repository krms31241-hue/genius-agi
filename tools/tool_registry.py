from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from .tool import Tool, HealthStatus


class ToolRegistry:
    """Central registry for dynamic tool management, search, and persistence."""

    def __init__(self) -> None:
        self._tools: Dict[str, Tool] = {}

    def _make_key(self, name: str, version: str) -> str:
        return f"{name}:{version}"

    def register(self, tool: Tool) -> None:
        """Register a tool. Raises ValueError on duplicate name+version."""
        key = self._make_key(tool.metadata.name, tool.metadata.version)
        if key in self._tools:
            raise ValueError(
                f"Tool '{tool.metadata.name}' v{tool.metadata.version} is already registered."
            )
        self._tools[key] = tool

    def remove(self, name: str, version: Optional[str] = None) -> bool:
        """Remove a specific version, or all versions if version is None."""
        if version:
            key = self._make_key(name, version)
            if key in self._tools:
                del self._tools[key]
                return True
            return False

        keys_to_remove = [
            k for k, t in self._tools.items() if t.metadata.name == name
        ]
        for k in keys_to_remove:
            del self._tools[k]
        return len(keys_to_remove) > 0

    def get(self, name: str, version: Optional[str] = None) -> Optional[Tool]:
        """Retrieve a tool. Returns latest version if version is omitted."""
        if version:
            return self._tools.get(self._make_key(name, version))

        matches = [t for t in self._tools.values() if t.metadata.name == name]
        if not matches:
            return None

        matches.sort(key=lambda t: t.metadata.version, reverse=True)
        return matches[0]

    def search_by_name(self, query: str) -> List[Tool]:
        """Case-insensitive substring search on tool names."""
        q = query.lower()
        return [t for t in self._tools.values() if q in t.metadata.name.lower()]

    def search_by_capability(self, capability: str) -> List[Tool]:
        """Exact match search on capabilities (case-insensitive)."""
        c = capability.lower()
        return [
            t for t in self._tools.values()
            if any(c == cap.lower() for cap in t.metadata.capabilities)
        ]

    def search_by_tags(self, tags: List[str], match_all: bool = False) -> List[Tool]:
        """Filter tools by tags. match_all=True requires every tag to be present."""
        target = {t.lower() for t in tags}
        results: List[Tool] = []
        for tool in self._tools.values():
            tool_tags = {t.lower() for t in tool.metadata.tags}
            if match_all:
                if target.issubset(tool_tags):
                    results.append(tool)
            else:
                if target & tool_tags:
                    results.append(tool)
        return results

    def enable(self, name: str, version: Optional[str] = None) -> bool:
        """Enable a tool. Returns False if not found."""
        tool = self.get(name, version)
        if tool:
            tool.enabled = True
            return True
        return False

    def disable(self, name: str, version: Optional[str] = None) -> bool:
        """Disable a tool. Returns False if not found."""
        tool = self.get(name, version)
        if tool:
            tool.enabled = False
            return True
        return False

    def get_all(self) -> List[Tool]:
        """Return a snapshot of all registered tools."""
        return list(self._tools.values())

    def serialize(self) -> Dict[str, object]:
        """Serialize runtime state (enabled, health, timestamps) to a dict."""
        state: Dict[str, object] = {}
        for key, tool in self._tools.items():
            state[key] = {
                "enabled": tool.enabled,
                "health_status": tool.health_status.value,
                "last_execution_timestamp": (
                    tool.last_execution_timestamp.isoformat()
                    if tool.last_execution_timestamp
                    else None
                ),
            }
        return state

    def deserialize(self, data: Dict[str, object]) -> None:
        """Apply serialized state to currently registered tools."""
        for key, raw_state in data.items():
            if key not in self._tools:
                continue
            tool = self._tools[key]
            state = raw_state if isinstance(raw_state, dict) else {}
            tool.enabled = bool(state.get("enabled", True))
            tool.health_status = HealthStatus(state.get("health_status", "unknown"))
            ts_str = state.get("last_execution_timestamp")
            if isinstance(ts_str, str):
                tool.last_execution_timestamp = datetime.fromisoformat(ts_str)

    def save_to_file(self, filepath: str) -> None:
        """Persist registry state to a JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.serialize(), f, indent=2)

    def load_from_file(self, filepath: str) -> None:
        """Restore registry state from a JSON file."""
        if not os.path.exists(filepath):
            return
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.deserialize(data)
