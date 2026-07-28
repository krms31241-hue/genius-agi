"""Comprehensive tests for Self Governance Engine."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from governance.governance_manager import GovernanceManager
from governance.policy import Policy
from governance.core_axioms import CoreAxiom, DEFAULT_AXIOMS

@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture
def manager(data_dir):
    return GovernanceManager(data_dir=data_dir)

def test_axiom_creation():
    axiom = CoreAxiom(id="test_ax", title="Test", description="Desc", priority=5)
    assert axiom.id == "test_ax"
    assert axiom.immutable is True
    assert axiom.to_dict()["title"] == "Test"

def test_policy_creation():
    pol = Policy(name="test_policy", version="1.0.0", rules=[{"type": "allow"}])
    assert pol.status == "draft"
    assert pol.id is not None
    assert pol.to_dict()["name"] == "test_policy"

def test_policy_registration(manager):
    pol = Policy(name="reg_test", version="1.0.0")
    assert manager.register_policy(pol) is True
    loaded = manager.load_policies()
    assert len(loaded) == 1
    assert loaded[0].name == "reg_test"

def test_enable_disable_policy(manager):
    pol = Policy(name="toggle_test", version="1.0.0")
    manager.register_policy(pol)
    assert manager.enable_policy(pol.id) is True
    active = manager.get_active_policies()
    assert any(p.id == pol.id for p in active)
    assert manager.disable_policy(pol.id) is True
    active = manager.get_active_policies()
    assert not any(p.id == pol.id for p in active)

def test_policy_history(manager):
    pol = Policy(name="hist_test", version="1.0.0")
    manager.register_policy(pol)
    manager.enable_policy(pol.id)
    hist = manager.get_history(pol.id)
    assert len(hist) >= 2
    assert hist[0]["action"] == "add"

def test_policy_rollback(manager):
    pol = Policy(name="roll_test", version="1.0.0")
    manager.register_policy(pol)
    manager.enable_policy(pol.id)
    pol.version = "2.0.0"
    manager.store.update(pol)
    assert manager.rollback_policy(pol.id, "1.0.0") is True
    latest = manager.store.latest(pol.id)
    assert latest.version == "1.0.0"

def test_persistence(data_dir):
    mgr1 = GovernanceManager(data_dir=data_dir)
    pol = Policy(name="persist_test", version="1.0.0")
    mgr1.register_policy(pol)
    mgr1.enable_policy(pol.id)

    mgr2 = GovernanceManager(data_dir=data_dir)
    loaded = mgr2.load_policies()
    assert len(loaded) == 1
    assert loaded[0].status == "active"

def test_validation(manager):
    valid = Policy(name="valid", version="1.0.0")
    assert manager.validate_policy(valid) is True
    invalid = Policy(name="", version="1.0.0")
    assert manager.validate_policy(invalid) is False

def test_manager_integration(manager):
    pol = Policy(name="integration", version="1.0.0", metrics={"test_pass_rate": 95})
    assert manager.register_policy(pol) is True
    eval_res = manager.evaluate_policy(pol)
    assert eval_res["compliant"] is True
    assert eval_res["score"] == 100.0
    assert manager.enable_policy(pol.id) is True
    assert len(manager.get_active_policies()) == 1
