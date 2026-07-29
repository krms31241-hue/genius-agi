"""Comprehensive tests for Runtime Optimizer."""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.runtime_optimizer import RuntimeOptimizer, RuntimeMetrics, OptimizationAction
from executive.resource_manager import ResourceManager
from executive.adaptive_scheduler import AdaptiveScheduler
from executive.task_graph import TaskGraph

@pytest.fixture
def optimizer():
    return RuntimeOptimizer(
        cpu_threshold=0.8, memory_threshold=0.8,
        latency_threshold=5.0, failure_threshold=0.2, queue_threshold=10
    )

def test_metrics_ingestion(optimizer):
    metrics = {"cpu_usage": 0.5, "memory_usage": 0.4, "queue_depth": 5}
    optimizer.update_metrics(metrics)
    assert optimizer.current_metrics.cpu_usage == 0.5
    assert optimizer.current_metrics.queue_depth == 5
    assert len(optimizer.history) == 1

def test_throttle_on_high_cpu(optimizer):
    optimizer.update_metrics({"cpu_usage": 0.9, "memory_usage": 0.3})
    recs = optimizer.analyze()
    assert len(recs) >= 1
    assert any(r.action_type == "throttle" for r in recs)
    assert optimizer.strategy_mode == "conservative"

def test_throttle_on_high_memory(optimizer):
    optimizer.update_metrics({"cpu_usage": 0.3, "memory_usage": 0.9})
    recs = optimizer.analyze()
    assert any(r.action_type == "throttle" for r in recs)

def test_stabilize_on_high_failures(optimizer):
    optimizer.update_metrics({"cpu_usage": 0.3, "memory_usage": 0.3, "failure_rate": 0.5})
    recs = optimizer.analyze()
    assert any(r.action_type == "stabilize" for r in recs)
    assert any(r.action_type == "backoff" for r in recs)

def test_optimize_on_high_latency(optimizer):
    optimizer.update_metrics({"cpu_usage": 0.3, "memory_usage": 0.3, "failure_rate": 0.0, "avg_latency": 10.0})
    recs = optimizer.analyze()
    assert any(r.action_type == "optimize" for r in recs)

def test_accelerate_on_queue_depth(optimizer):
    # Low resources, high queue
    optimizer.update_metrics({"cpu_usage": 0.2, "memory_usage": 0.2, "queue_depth": 50})
    recs = optimizer.analyze()
    assert any(r.action_type == "accelerate" for r in recs)
    assert optimizer.strategy_mode == "aggressive"

def test_normalize_to_balanced(optimizer):
    # Start aggressive
    optimizer.strategy_mode = "aggressive"
    # Normal metrics
    optimizer.update_metrics({"cpu_usage": 0.5, "memory_usage": 0.5, "queue_depth": 5, "failure_rate": 0.0})
    recs = optimizer.analyze()
    assert any(r.action_type == "normalize" for r in recs)
    assert optimizer.strategy_mode == "balanced"

def test_apply_optimizations_resource_mgr(optimizer):
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(data_dir=tmpdir, budgets={"max_concurrent": 4})
        optimizer.update_metrics({"cpu_usage": 0.9})
        optimizer.analyze()
        result = optimizer.apply_optimizations(resource_mgr=rm)
        assert "Reduced concurrency" in result["applied"][0]
        assert rm.budgets["max_concurrent"] == 2

def test_apply_optimizations_scheduler(optimizer):
    g = TaskGraph()
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        rm = ResourceManager(data_dir=tmpdir)
        sched = AdaptiveScheduler(g, rm)
        sched.metadata = {}
        optimizer.update_metrics({"failure_rate": 0.5})
        optimizer.analyze()
        result = optimizer.apply_optimizations(scheduler=sched)
        assert "stabilization_mode" in result["applied"][0]
        assert sched.metadata.get("stabilization_mode") is True

def test_priority_ordering(optimizer):
    # Trigger multiple conditions to check priority sorting if implemented
    # Here we just verify recommendations are generated
    optimizer.update_metrics({"cpu_usage": 0.9, "failure_rate": 0.5})
    recs = optimizer.analyze()
    # CPU throttle should take precedence or be present
    assert any(r.priority >= 8 for r in recs)
