"""Comprehensive tests for Execution Policy Enforcement."""
import os
import sys
import time
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.execution_policy import ExecutionPolicyEnforcer
from governance.governance_manager import GovernanceManager
from governance.policy import Policy

@pytest.fixture
def governance_mgr():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield GovernanceManager(data_dir=os.path.join(tmpdir, "gov"))

@pytest.fixture
def enforcer(governance_mgr):
    return ExecutionPolicyEnforcer(governance_mgr)

def test_allowed_execution_no_policies(enforcer):
    ctx = {"mode": "production", "risk": 0.5}
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is True
    assert len(res["violations"]) == 0
    assert len(res["checked_policies"]) == 0

def test_allowed_execution_with_policy(enforcer):
    pol = Policy(name="safe_exec", version="1.0.0", rules=[
        {"type": "threshold", "target": "risk", "value": 0.8},
        {"type": "constraint", "target": "sandbox", "value": "required"}
    ])
    enforcer.register_and_enable_policy(pol)
    
    ctx = {"risk": 0.5, "sandbox": True}
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is True
    assert len(res["violations"]) == 0
    assert pol.id in res["checked_policies"]

def test_denied_execution_threshold(enforcer):
    pol = Policy(name="risk_limit", version="1.0.0", rules=[
        {"type": "threshold", "target": "cpu_usage", "value": 80.0}
    ])
    enforcer.register_and_enable_policy(pol)
    
    ctx = {"cpu_usage": 95.0}
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is False
    assert len(res["violations"]) == 1
    assert "threshold" in res["violations"][0]["reason"]

def test_denied_execution_constraint(enforcer):
    pol = Policy(name="sandbox_only", version="1.0.0", rules=[
        {"type": "constraint", "target": "execution_mode", "value": "sandbox_only"}
    ])
    enforcer.register_and_enable_policy(pol)
    
    ctx = {"execution_mode": "production"}
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is False
    assert len(res["violations"]) == 1

def test_denied_execution_deny_list(enforcer):
    pol = Policy(name="block_actions", version="1.0.0", rules=[
        {"type": "deny", "target": "action", "value": ["rm_rf", "format_disk"]}
    ])
    enforcer.register_and_enable_policy(pol)
    
    ctx = {"action": "rm_rf"}
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is False
    assert "deny" in res["violations"][0]["reason"]

def test_policy_updates(enforcer):
    pol = Policy(name="dynamic_rule", version="1.0.0", rules=[
        {"type": "threshold", "target": "memory_mb", "value": 256}
    ])
    enforcer.register_and_enable_policy(pol)
    
    ctx = {"memory_mb": 300}
    assert enforcer.validate_execution(ctx)["allowed"] is False
    
    # Update policy to allow higher memory
    enforcer.update_policy_rules(pol.id, [{"type": "threshold", "target": "memory_mb", "value": 512}])
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is True

def test_policy_rollback(enforcer):
    pol = Policy(name="rollback_test", version="1.0.0", rules=[
        {"type": "deny", "target": "net_access", "value": False}
    ])
    enforcer.register_and_enable_policy(pol)
    
    # Update to stricter version
    pol.version = "2.0.0"
    enforcer.governance.store.update(pol)
    enforcer.update_policy_rules(pol.id, [{"type": "deny", "target": "net_access", "value": True}])
    
    ctx = {"net_access": True}
    assert enforcer.validate_execution(ctx)["allowed"] is False
    
    # Rollback to v1.0.0
    assert enforcer.rollback_policy(pol.id, "1.0.0") is True
    res = enforcer.validate_execution(ctx)
    assert res["allowed"] is True

def test_multiple_policies_interaction(enforcer):
    p1 = Policy(name="cpu_guard", version="1.0.0", rules=[{"type": "threshold", "target": "cpu", "value": 70}])
    p2 = Policy(name="mem_guard", version="1.0.0", rules=[{"type": "threshold", "target": "mem", "value": 500}])
    enforcer.register_and_enable_policy(p1)
    enforcer.register_and_enable_policy(p2)
    
    ctx_ok = {"cpu": 50, "mem": 400}
    assert enforcer.validate_execution(ctx_ok)["allowed"] is True
    
    ctx_fail = {"cpu": 80, "mem": 600}
    res = enforcer.validate_execution(ctx_fail)
    assert res["allowed"] is False
    assert len(res["violations"]) == 2
