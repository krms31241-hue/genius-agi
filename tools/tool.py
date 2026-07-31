from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from .tool_metadata import ToolMetadata
from .tool_result import ToolResult


class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class Tool:
    metadata: ToolMetadata
    enabled: bool = True
    health_status: HealthStatus = HealthStatus.UNKNOWN
    last_execution_timestamp: datetime | None = None

    @abstractmethod
    def execute(self, inputs) -> ToolResult:
        raise NotImplementedError

    def __init_subclass__(cls):
        super().__init_subclass__()

        if "execute" in cls.__dict__:
            original = cls.__dict__["execute"]

            def wrapped(self, inputs):
                result = original(self, inputs)
                self.record_execution(result)
                return result

            cls.execute = wrapped

    def record_execution(self, result: ToolResult):
        self.last_execution_timestamp = datetime.now(timezone.utc)

        if result.success:
            self.health_status = HealthStatus.HEALTHY
        else:
            self.health_status = HealthStatus.UNHEALTHY
