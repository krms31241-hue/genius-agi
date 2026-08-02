from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any


class ResourceMode(str, Enum):
    ECO = "eco"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    CUSTOM = "custom"


@dataclass
class ResourceLimits:
    cpu_percent: float
    memory_percent: float
    disk_percent: float


DEFAULT_LIMITS = {
    ResourceMode.ECO: ResourceLimits(
        cpu_percent=50.0,
        memory_percent=50.0,
        disk_percent=40.0,
    ),
    ResourceMode.BALANCED: ResourceLimits(
        cpu_percent=75.0,
        memory_percent=75.0,
        disk_percent=70.0,
    ),
    ResourceMode.PERFORMANCE: ResourceLimits(
        cpu_percent=95.0,
        memory_percent=95.0,
        disk_percent=90.0,
    ),
}


class ResourcePolicy:
    """
    Decides how much of the user's machine Genius AGI
    is allowed to consume.
    """

    def __init__(
        self,
        mode: ResourceMode = ResourceMode.BALANCED,
        custom: ResourceLimits | None = None,
    ):
        self.mode = mode

        if mode == ResourceMode.CUSTOM:
            if custom is None:
                raise ValueError("CUSTOM mode requires custom limits.")
            self.limits = custom
        else:
            self.limits = DEFAULT_LIMITS[mode]

    def evaluate(self, system: Dict[str, Any]) -> Dict[str, Any]:

        cpu = system.get("cpu", {})
        mem = system.get("memory", {})
        disk = system.get("disk", {})

        cpu_now = cpu.get("current_cpu_usage_percent", 0.0)
        mem_now = mem.get("percent", 0.0)
        disk_now = disk.get("percent", 0.0)

        return {
            "mode": self.mode.value,
            "allow_new_tasks": (
                cpu_now < self.limits.cpu_percent
                and mem_now < self.limits.memory_percent
                and disk_now < self.limits.disk_percent
            ),
            "limits": {
                "cpu": self.limits.cpu_percent,
                "memory": self.limits.memory_percent,
                "disk": self.limits.disk_percent,
            },
            "current": {
                "cpu": cpu_now,
                "memory": mem_now,
                "disk": disk_now,
            },
            "pressure": {
                "cpu": cpu_now / self.limits.cpu_percent
                if self.limits.cpu_percent else 0,
                "memory": mem_now / self.limits.memory_percent
                if self.limits.memory_percent else 0,
                "disk": disk_now / self.limits.disk_percent
                if self.limits.disk_percent else 0,
            },
        }

    def should_request_user_permission(
        self,
        system: Dict[str, Any],
    ) -> bool:

        result = self.evaluate(system)

        return (
            result["current"]["cpu"] > result["limits"]["cpu"]
            or result["current"]["memory"] > result["limits"]["memory"]
            or result["current"]["disk"] > result["limits"]["disk"]
        )
