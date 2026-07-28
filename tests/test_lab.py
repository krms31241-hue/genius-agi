"""Validation tests for the Code Laboratory."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from lab.orchestrator import CodeLaboratory
from lab.watchdog import Watchdog, WatchdogTimeout
from lab.failure_db import FailureDB
from lab.analyzers.syntax import SyntaxAnalyzer
from lab.analyzers.security import SecurityAnalyzer

def test_syntax_analyzer_pass():
    res = SyntaxAnalyzer().analyze("def hello():\n    return 42", "test.py", {})
    from pprint import pprint
    print("\n========== RESULT ==========")
    pprint(res)
    print("============================\n")

    assert res["passed"] is True
    assert res["score"] == 100

def test_syntax_analyzer_fail():
    res = SyntaxAnalyzer().analyze("def hello(\n    return 42", "test.py", {})
    assert res["passed"] is False
    assert "SyntaxError" in res["issues"][0]

def test_security_analyzer_safe():
    res = SecurityAnalyzer().analyze("import os\nprint('safe')", "test.py", {})
    assert res["passed"] is True

def test_security_analyzer_unsafe():
    res = SecurityAnalyzer().analyze("eval('1+1')", "test.py", {})
    assert res["passed"] is False
    assert any("eval" in i for i in res["issues"])

def test_failure_db_learning():
    db = FailureDB(":memory:")
    code = "bad_code()"
    assert db.is_known_failure(code) is None
    db.learn_and_block(code, "test_error", "details")
    known = db.is_known_failure(code)
    assert known is not None
    assert known["error_type"] == "test_error"

def test_watchdog_timeout():
    import time
    wd = Watchdog(timeout_sec=0.5)
    def slow():
        time.sleep(2)
        return "done"
    with pytest.raises(WatchdogTimeout):
        wd.run(slow)

def test_orchestrator_rejects_bad_patch():
    lab = CodeLaboratory(timeout_sec=5.0, sandbox_timeout=3.0)
    bad = {"main.py": "eval('danger')\nwhile True: pass"}
    res = lab.validate_patch(bad, "main.py", {"patch_id": "test_bad"})
    assert res["passed"] is False
    assert res.get("rejected") is True

def test_orchestrator_accepts_safe_patch():
    lab = CodeLaboratory(timeout_sec=10.0, sandbox_timeout=5.0)
    safe = {"main.py": "def run():\n    return 'ok'\nif __name__ == '__main__':\n    print(run())"}
    res = lab.validate_patch(safe, "main.py", {"patch_id": "test_safe"})

    from pprint import pprint
    print("\n========== RESULT ==========")
    pprint(res)
    print("============================\n")
    assert res["passed"] is True
    assert res["scores"]["confidence"] > 70
