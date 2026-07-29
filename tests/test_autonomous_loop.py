"""Comprehensive tests for Autonomous Executive Loop."""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from executive.autonomous_loop import AutonomousLoop
from executive.loop_controller import LoopController
from executive.loop_state import LoopState, LoopPhase, LoopStatus

def make_handlers(fail_phase=None, fail_count=0, stop_after=None):
    calls = {p.value: 0 for p in LoopPhase}
    failure_tracker = {"count": 0}

    def handler(phase_name):
        def fn(state, ctx):
            calls[phase_name] += 1
            if fail_phase == phase_name and failure_tracker["count"] < fail_count:
                failure_tracker["count"] += 1
                raise RuntimeError(f"Simulated {phase_name} failure")
            if stop_after and calls[phase_name] >= stop_after:
                state.stop_requested = True
            return {f"{phase_name}_done": True}
        return fn

    return calls, {p: handler(p.value) for p in LoopPhase}

def test_continuous_loop():
    calls, handlers = make_handlers()
    ctrl = LoopController(max_iterations=3, max_duration_sec=10.0)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.COMPLETED
    assert state.iteration == 3
    assert state.total_successes == 3
    assert all(v == 3 for v in calls.values())

def test_failure_and_recovery():
    calls, handlers = make_handlers(fail_phase="execute", fail_count=2)
    ctrl = LoopController(max_iterations=5, max_consecutive_failures=10)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.COMPLETED
    assert state.total_failures == 2
    assert state.total_recoveries == 2
    assert state.total_successes == 3

def test_safe_stop():
    calls, handlers = make_handlers(stop_after=2)
    ctrl = LoopController(max_iterations=10)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.STOPPED
    assert state.iteration == 1
    assert state.stop_requested is True

def test_iteration_limits():
    calls, handlers = make_handlers()
    ctrl = LoopController(max_iterations=2, max_duration_sec=10.0)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.COMPLETED
    assert state.iteration == 2

def test_watchdog_timeout():
    def slow_handler(state, ctx):
        time.sleep(0.3)
        return {}
    handlers = {p: slow_handler for p in LoopPhase}
    ctrl = LoopController(max_iterations=1, watchdog_timeout_sec=0.2)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.COMPLETED
    assert state.total_failures >= 1
    assert any("Watchdog timeout" in e for e in state.errors)

def test_consecutive_failure_limit():
    calls, handlers = make_handlers(fail_phase="plan", fail_count=10)
    ctrl = LoopController(max_iterations=10, max_consecutive_failures=3)
    loop = AutonomousLoop(ctrl, **handlers)
    state = loop.run()
    assert state.status == LoopStatus.FAILED
    assert state.consecutive_failures >= 3

def test_loop_statistics():
    calls, handlers = make_handlers()
    ctrl = LoopController(max_iterations=2, max_duration_sec=10.0)
    loop = AutonomousLoop(ctrl, **handlers)
    loop.run()
    stats = loop.get_statistics()
    assert stats["iteration"] == 2
    assert stats["total_successes"] == 2
    assert stats["runtime_sec"] > 0.0
    assert "observe" in stats["phase_durations"]
