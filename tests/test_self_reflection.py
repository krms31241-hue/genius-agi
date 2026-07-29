"""Comprehensive tests for Self Reflection Engine."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.reflection_report import ReflectionReport
from executive.improvement_engine import ImprovementEngine
from executive.self_reflection import SelfReflectionEngine

@pytest.fixture
def memory_adapter():
    """Real MemoryManager instance for integration testing."""
    from memory.memory_manager import MemoryManager
    with tempfile.TemporaryDirectory() as tmpdir:
        # MemoryManager expects db_path, not data_dir
        db_file = os.path.join(tmpdir, "mem.db")
        yield MemoryManager(db_path=db_file)

def test_reflection_report_creation():
    report = ReflectionReport(
        execution_id="exec_1",
        success_rate=0.85,
        failure_count=2,
        efficiency_score=0.72,
        mistakes=["timeout in task_a"],
        lessons=["Optimize long-running tasks"],
        improvement_proposals=[{"type": "optimization", "action": "batch tasks"}]
    )
    d = report.to_dict()
    assert d["execution_id"] == "exec_1"
    assert d["success_rate"] == 0.85
    restored = ReflectionReport.from_dict(d)
    assert restored.efficiency_score == 0.72
    assert len(restored.mistakes) == 1

def test_self_reflection_success_analysis():
    engine = SelfReflectionEngine()
    data = {
        "completed": ["t1", "t2", "t3", "t4", "t5"],
        "failed": [],
        "total_duration": 2.0,
        "errors": {}
    }
    report = engine.reflect("exec_success", data)
    assert report.success_rate == 1.0
    assert report.failure_count == 0
    assert report.efficiency_score > 0.0
    assert any("High success rate" in l for l in report.lessons)

def test_self_reflection_failure_and_mistakes():
    engine = SelfReflectionEngine()
    data = {
        "completed": ["t1"],
        "failed": ["t2", "t3", "t4"],
        "total_duration": 5.0,
        "errors": {"t2": "Connection timeout reached", "t3": "Memory budget exceeded", "t4": "Connection timeout reached"}
    }
    report = engine.reflect("exec_fail", data)
    assert report.success_rate == 0.25
    assert report.failure_count == 3
    # Deduplicated mistakes
    assert len(report.mistakes) == 2
    assert any("Timeouts detected" in l for l in report.lessons)
    assert any("Resource constraints" in l for l in report.lessons)

def test_improvement_engine_proposals():
    engine = ImprovementEngine()
    report = ReflectionReport(
        execution_id="exec_imp",
        success_rate=0.4,
        failure_count=4,
        efficiency_score=0.3,
        mistakes=["dependency cycle detected"]
    )
    proposals = engine.analyze_and_propose(report)
    assert len(proposals) >= 4
    types = [p["type"] for p in proposals]
    assert "strategy" in types
    assert "optimization" in types
    assert "reliability" in types
    assert "correction" in types

def test_memory_integration(memory_adapter):
    engine = SelfReflectionEngine()
    data = {
        "completed": ["t1", "t2"],
        "failed": ["t3"],
        "total_duration": 1.5,
        "errors": {"t3": "transient network glitch"}
    }
    report = engine.reflect("exec_mem", data, memory_adapter=memory_adapter)
    assert len(report.lessons) > 0
    assert len(report.improvement_proposals) > 0
    
    # Verify lessons were persisted to semantic memory
    stored_facts = memory_adapter.search_facts("Lesson from exec_mem")
    assert len(stored_facts) == len(report.lessons)
    assert all("self_reflection" in f.source for f in stored_facts)

def test_efficiency_calculation():
    engine = SelfReflectionEngine()
    # High throughput, low duration -> high efficiency
    data_fast = {"completed": ["a","b","c","d","e"], "failed": [], "total_duration": 0.5, "errors": {}}
    r_fast = engine.reflect("eff_fast", data_fast)
    assert r_fast.efficiency_score == 1.0
    
    # Low throughput, high duration -> low efficiency
    data_slow = {"completed": ["a"], "failed": ["b","c"], "total_duration": 10.0, "errors": {}}
    r_slow = engine.reflect("eff_slow", data_slow)
    assert r_slow.efficiency_score < 0.2

def test_latest_report_tracking():
    engine = SelfReflectionEngine()
    assert engine.get_latest_report() is None
    engine.reflect("exec_track", {"completed": ["x"], "failed": [], "total_duration": 1.0, "errors": {}})
    latest = engine.get_latest_report()
    assert latest is not None
    assert latest.execution_id == "exec_track"
