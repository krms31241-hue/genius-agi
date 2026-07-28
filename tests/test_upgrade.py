"""Verification tests for Automatic Upgrade Manager."""
import os
import sys
import json
import pytest
import tempfile
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from upgrade.resource_guard import ResourceGuard
from upgrade.crash_recovery import CrashRecovery
from upgrade.snapshot_manager import SnapshotManager
from upgrade.inspector import ProjectInspector
from upgrade.comparator import VersionComparator

def test_resource_guard_limits():
    guard = ResourceGuard(max_cpu_sec=2.0, max_memory_mb=256)
    guard.apply_limits()
    guard.check_cpu_time()  # Should not raise immediately
    guard.release_limits()

def test_resource_guard_deadlock_detection():
    import threading
    guard = ResourceGuard()
    lock = threading.Lock()
    lock.acquire()
    with pytest.raises(RuntimeError, match="Deadlock detected"):
        guard.acquire_lock(lock, "test_lock", timeout=0.1)
    lock.release()

def test_crash_recovery_flow():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    try:
        rec = CrashRecovery(path)
        rec.save("validating", snap_id="snap_1")
        assert rec.is_interrupted() is True
        action = rec.get_recovery_action()
        assert action["action"] == "rollback"
        rec.clear()
        assert rec.is_interrupted() is False
    finally:
        os.unlink(path)

def test_snapshot_manager_atomic_ops():
    with tempfile.TemporaryDirectory() as tmpdir:
        proj = os.path.join(tmpdir, "proj")
        os.makedirs(proj)
        with open(os.path.join(proj, "main.py"), "w") as f:
            f.write("print('v1')")
        sm = SnapshotManager(os.path.join(tmpdir, "versions"))
        snap = sm.create_snapshot(proj)
        assert os.path.exists(os.path.join(tmpdir, "versions", snap))
        # Modify project
        with open(os.path.join(proj, "main.py"), "w") as f:
            f.write("print('v2')")
        # Rollback
        assert sm.rollback(snap, proj) is True
        with open(os.path.join(proj, "main.py")) as f:
            assert "v1" in f.read()

def test_inspector_metrics():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "app.py"), "w") as f:
            f.write("def run():\n    if True:\n        pass\n")
        insp = ProjectInspector()
        m = insp.inspect(tmpdir)
        assert m["total_lines"] > 0
        assert len(m["files"]) == 1
        assert m["complexity_score"] >= 1

def test_comparator_decision():
    comp = VersionComparator()
    baseline = {"duration_sec": 2.0, "success": True}
    candidate = {"duration_sec": 1.0, "success": True}
    lab = {"passed": True, "scores": {"security": 90, "maintainability": 80}}
    res = comp.compare(baseline, candidate, lab)
    assert res["decision"] == "APPROVE"
    assert res["safe_to_upgrade"] is True

def test_comparator_rejects_worse():
    comp = VersionComparator()
    baseline = {"duration_sec": 1.0, "success": True}
    candidate = {"duration_sec": 3.0, "success": True}
    lab = {"passed": True, "scores": {"security": 60, "maintainability": 50}}
    res = comp.compare(baseline, candidate, lab)
    assert res["decision"] == "REJECT"
