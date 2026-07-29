"""Comprehensive tests for Policy Evolution Engine."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from governance.governance_manager import GovernanceManager
from governance.policy_evolution import PolicyEvolutionEngine, EvolutionReport
from governance.policy_generator import PolicyGenerator
from governance.policy_mutation import PolicyMutation
from governance.policy_optimizer import PolicyOptimizer
from governance.policy_simulator import PolicySimulator
from governance.policy_validator import PolicyValidator
from governance.policy import Policy
from governance.core_axioms import DEFAULT_AXIOMS

@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def governance(data_dir):
    return GovernanceManager(data_dir=os.path.join(data_dir, "gov"))

@pytest.fixture
def engine(governance, data_dir):
    return PolicyEvolutionEngine(governance=governance, evolution_dir=os.path.join(data_dir, "evo"))

@pytest.fixture
def context():
    return {
        "memory_stats": {"recall_rate": 60},
        "decision_stats": {"avg_confidence": 0.5},
        "failure_stats": {"recent_failures": 8},
        "upgrade_stats": {"rollback_rate": 0.3}
    }

def test_policy_generation(context):
    gen = PolicyGenerator()
    policies = gen.generate(context)
    assert len(policies) >= 2
    assert all(p.status == "draft" for p in policies)

def test_policy_mutation():
    mut = PolicyMutation()
    base = Policy(name="mut_test", version="1.0.0", rules=[{"type": "threshold", "value": 0.5}], metrics={"priority": "medium"})
    mutated = mut.mutate(base, seed="test_seed")
    assert mutated.id != base.id
    assert mutated.version == "1.0.1"
    assert "mutated:" in mutated.description

def test_policy_optimizer(context):
    opt = PolicyOptimizer(population_size=4, survival_rate=0.5)
    base = Policy(name="opt_test", version="1.0.0", rules=[{"type": "threshold", "value": 0.6}], metrics={"priority": "high"})
    survivors = opt.optimize(base, context)
    assert len(survivors) == 2
    assert all(s.score > 0 for s in survivors)

def test_policy_simulator():
    sim = PolicySimulator()
    pol = Policy(name="sim_test", rules=[{"type": "constraint", "target": "safety", "value": "strict"}], metrics={"priority": "high"})
    metrics = sim.simulate(pol, {})
    assert "performance" in metrics
    assert "stability" in metrics
    assert "failure_rate" in metrics
    assert all(0.0 <= v <= 1.0 for v in metrics.values())

def test_policy_validator():
    val = PolicyValidator(axioms=DEFAULT_AXIOMS, baseline_metrics={"test_success": 0.9, "stability": 0.8, "failure_rate": 0.2})
    pol = Policy(name="val_test", rules=[], metrics={})
    good_metrics = {"failure_rate": 0.1, "stability": 0.9, "rollback_rate": 0.1, "performance": 0.8}
    res = val.validate(pol, good_metrics)
    assert res["passed"] is True
    
    bad_metrics = {"failure_rate": 0.5, "stability": 0.5, "rollback_rate": 0.6, "performance": 0.8}
    res_bad = val.validate(pol, bad_metrics)
    assert res_bad["passed"] is False
    assert len(res_bad["violations"]) > 0

def test_full_evolution_cycle(engine, context):
    report = engine.run_cycle(context)
    assert report.status == "success"
    assert report.promoted_policy is not None
    assert report.promoted_policy["status"] == "active"
    assert len(report.reasoning) >= 3
    assert "performance" in report.metrics
    assert os.path.exists(os.path.join(engine.reports_dir, f"{report.cycle_id}.json"))

def test_evolution_archival_and_rollback_info(engine, context):
    r1 = engine.run_cycle(context)
    assert r1.status == "success"
    r2 = engine.run_cycle(context)
    assert r2.status == "success"
    assert r2.archived_policy is not None
    assert r2.archived_policy["id"] == r1.promoted_policy["id"]
    assert len(r2.rollback_info["previous_active"]) > 0

def test_evolution_persistence(engine, context):
    report = engine.run_cycle(context)
    metrics_path = os.path.join(engine.metrics_dir, f"{report.cycle_id}.json")
    assert os.path.exists(metrics_path)
    import json
    with open(metrics_path) as f:
        data = json.load(f)
    assert "stability" in data
