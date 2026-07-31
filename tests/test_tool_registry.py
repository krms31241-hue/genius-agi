from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from typing import Dict

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.tool_metadata import ToolMetadata
from tools.tool_result import ToolResult
from tools.tool import Tool, HealthStatus
from tools.tool_registry import ToolRegistry


class MockTool(Tool):
    """Concrete implementation for testing purposes."""
    def execute(self, inputs: Dict[str, object]) -> ToolResult:
        return ToolResult(success=True, data={"echo": inputs})


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def sample_tool() -> MockTool:
    return MockTool(
        metadata=ToolMetadata(
            name="calculator",
            version="1.0.0",
            description="Basic math operations",
            capabilities=["math", "compute"],
            tags=["utility", "core"],
            required_permissions=["read"],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )
    )


class TestRegistration:
    def test_register_tool(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        assert registry.get("calculator", "1.0.0") is sample_tool

    def test_duplicate_protection(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(sample_tool)

    def test_remove_specific_version(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        assert registry.remove("calculator", "1.0.0") is True
        assert registry.get("calculator", "1.0.0") is None

    def test_remove_all_versions(self, registry: ToolRegistry) -> None:
        t1 = MockTool(metadata=ToolMetadata(name="calc", version="1.0.0"))
        t2 = MockTool(metadata=ToolMetadata(name="calc", version="2.0.0"))
        registry.register(t1)
        registry.register(t2)
        assert registry.remove("calc") is True
        assert registry.get("calc", "1.0.0") is None
        assert registry.get("calc", "2.0.0") is None

    def test_remove_nonexistent(self, registry: ToolRegistry) -> None:
        assert registry.remove("ghost", "1.0.0") is False


class TestLookupAndFiltering:
    @pytest.fixture(autouse=True)
    def _setup_tools(self, registry: ToolRegistry) -> None:
        self.t1 = MockTool(metadata=ToolMetadata(name="calc", version="1.0.0", capabilities=["math"], tags=["util"]))
        self.t2 = MockTool(metadata=ToolMetadata(name="calc", version="2.0.0", capabilities=["math", "advanced"], tags=["util", "new"]))
        self.t3 = MockTool(metadata=ToolMetadata(name="translator", version="1.0.0", capabilities=["lang"], tags=["util"]))
        registry.register(self.t1)
        registry.register(self.t2)
        registry.register(self.t3)

    def test_get_specific_version(self, registry: ToolRegistry) -> None:
        assert registry.get("calc", "1.0.0") is self.t1
        assert registry.get("calc", "2.0.0") is self.t2

    def test_get_latest_version(self, registry: ToolRegistry) -> None:
        assert registry.get("calc") is self.t2

    def test_search_by_name(self, registry: ToolRegistry) -> None:
        results = registry.search_by_name("calc")
        assert len(results) == 2

    def test_search_by_capability(self, registry: ToolRegistry) -> None:
        results = registry.search_by_capability("advanced")
        assert len(results) == 1
        assert results[0] is self.t2

    def test_search_by_tags_any(self, registry: ToolRegistry) -> None:
        results = registry.search_by_tags(["new"])
        assert len(results) == 1
        assert results[0] is self.t2

    def test_search_by_tags_all(self, registry: ToolRegistry) -> None:
        results = registry.search_by_tags(["util", "new"], match_all=True)
        assert len(results) == 1
        assert results[0] is self.t2


class TestEnableDisable:
    def test_enable_disable(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        assert sample_tool.enabled is True
        assert registry.disable("calculator", "1.0.0") is True
        assert sample_tool.enabled is False
        assert registry.enable("calculator", "1.0.0") is True
        assert sample_tool.enabled is True

    def test_enable_nonexistent(self, registry: ToolRegistry) -> None:
        assert registry.enable("missing") is False


class TestExecutionAndHealth:
    def test_execution_updates_state(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        result = sample_tool.execute({"x": 1})
        assert result.success is True
        assert sample_tool.health_status == HealthStatus.HEALTHY
        assert sample_tool.last_execution_timestamp is not None

    def test_failed_execution_updates_health(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        fail_res = ToolResult(success=False, error="division by zero")
        sample_tool.record_execution(fail_res)
        assert sample_tool.health_status == HealthStatus.UNHEALTHY


class TestSerializationAndPersistence:
    def test_serialize_deserialize(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        sample_tool.enabled = False
        sample_tool.health_status = HealthStatus.DEGRADED
        sample_tool.last_execution_timestamp = datetime(2024, 1, 1, tzinfo=timezone.utc)

        data = registry.serialize()
        assert data["calculator:1.0.0"]["enabled"] is False
        assert data["calculator:1.0.0"]["health_status"] == "degraded"

        sample_tool.enabled = True
        sample_tool.health_status = HealthStatus.UNKNOWN
        sample_tool.last_execution_timestamp = None

        registry.deserialize(data)
        assert sample_tool.enabled is False
        assert sample_tool.health_status == HealthStatus.DEGRADED
        assert sample_tool.last_execution_timestamp == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_persistence_to_file(self, registry: ToolRegistry, sample_tool: MockTool) -> None:
        registry.register(sample_tool)
        sample_tool.enabled = False

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            filepath = f.name

        try:
            registry.save_to_file(filepath)
            assert os.path.exists(filepath)

            new_reg = ToolRegistry()
            new_reg.register(sample_tool)
            new_reg.load_from_file(filepath)

            loaded_tool = new_reg.get("calculator", "1.0.0")
            assert loaded_tool is not None
            assert loaded_tool.enabled is False
        finally:
            os.unlink(filepath)
