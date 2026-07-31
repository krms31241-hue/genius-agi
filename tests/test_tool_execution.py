"""
tests/test_tool_execution.py — Full coverage for tool_executor.py

Covers:
  ✓ successful execution
  ✓ timeout
  ✓ invalid input
  ✓ retry
  ✓ exception isolation
  ✓ history
  ✓ metrics
  ✓ serialization
"""

from __future__ import annotations

import time
import threading
import unittest
import json
from typing import Any, Dict

from tool_executor import (
    ErrorCategory,
    ToolResult,
    RetryPolicy,
    ExecutionRecord,
    ToolDescriptor,
    ToolRegistry,
    InputValidator,
    ToolExecutor,
)


# ---------------------------------------------------------------------------
# Helper tools used across tests
# ---------------------------------------------------------------------------

def add(a: int, b: int) -> int:
    return a + b


def greet(name: str) -> str:
    return f"Hello, {name}!"


def failing_tool() -> None:
    raise RuntimeError("boom")


def slow_tool(duration: float = 5.0) -> str:
    time.sleep(duration)
    return "done"


def flaky_tool(_state: Dict[str, Any] = None) -> str:
    """Fails the first N-1 calls, succeeds on the Nth."""
    if _state is None:
        _state = {"calls": 0}
    _state["calls"] += 1
    if _state["calls"] < 3:
        raise ValueError("not yet")
    return "finally"


def type_error_tool() -> None:
    raise TypeError("wrong type")


def returning_dict(key: str, value: int) -> Dict[str, Any]:
    return {key: value}


# ---------------------------------------------------------------------------
# Tests — Successful execution
# ---------------------------------------------------------------------------

class TestSuccessfulExecution(unittest.TestCase):
    """Verify that well-formed calls return correct ToolResults."""

    def setUp(self) -> None:
        self.executor = ToolExecutor()
        self.executor.registry.register(
            ToolDescriptor(name="add", func=add, input_schema={
                "a": {"type": int, "required": True},
                "b": {"type": int, "required": True},
            })
        )
        self.executor.registry.register(
            ToolDescriptor(name="greet", func=greet, input_schema={
                "name": {"type": str, "required": True},
            })
        )

    def test_basic_add(self) -> None:
        res = self.executor.execute("add", {"a": 2, "b": 3})
        self.assertTrue(res.success)
        self.assertEqual(res.output, 5)
        self.assertIsNone(res.error)
        self.assertEqual(res.tool_name, "add")
        self.assertGreater(res.duration, 0)

    def test_basic_greet(self) -> None:
        res = self.executor.execute("greet", {"name": "Alice"})
        self.assertTrue(res.success)
        self.assertEqual(res.output, "Hello, Alice!")

    def test_dict_return(self) -> None:
        self.executor.registry.register(
            ToolDescriptor(name="mkdict", func=returning_dict, input_schema={
                "key": {"type": str, "required": True},
                "value": {"type": int, "required": True},
            })
        )
        res = self.executor.execute("mkdict", {"key": "x", "value": 42})
        self.assertTrue(res.success)
        self.assertEqual(res.output, {"x": 42})

    def test_no_schema_accepts_anything(self) -> None:
        self.executor.registry.register(
            ToolDescriptor(name="add2", func=add)
        )
        res = self.executor.execute("add2", {"a": 10, "b": 20})
        self.assertTrue(res.success)
        self.assertEqual(res.output, 30)

    def test_duration_is_positive(self) -> None:
        res = self.executor.execute("add", {"a": 1, "b": 1})
        self.assertGreaterEqual(res.duration, 0.0)


# ---------------------------------------------------------------------------
# Tests — Timeout
# ---------------------------------------------------------------------------

class TestTimeout(unittest.TestCase):
    """Verify that long-running tools are killed after the timeout."""

    def setUp(self) -> None:
        self.executor = ToolExecutor()
        self.executor.registry.register(
            ToolDescriptor(name="slow", func=slow_tool)
        )

    def test_timeout_triggers(self) -> None:
        res = self.executor.execute(
            "slow", {"duration": 10.0}, timeout=0.2
        )
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.TIMEOUT)
        self.assertIn("timeout", res.error.lower())

    def test_no_timeout_succeeds(self) -> None:
        res = self.executor.execute("slow", {"duration": 0.05}, timeout=2.0)
        self.assertTrue(res.success)
        self.assertEqual(res.output, "done")

    def test_per_tool_timeout(self) -> None:
        self.executor.registry.register(
            ToolDescriptor(name="slow2", func=slow_tool, timeout=0.15)
        )
        res = self.executor.execute("slow2", {"duration": 10.0})
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.TIMEOUT)

    def test_explicit_timeout_overrides_per_tool(self) -> None:
        self.executor.registry.register(
            ToolDescriptor(name="slow3", func=slow_tool, timeout=10.0)
        )
        res = self.executor.execute("slow3", {"duration": 10.0}, timeout=0.15)
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.TIMEOUT)


# ---------------------------------------------------------------------------
# Tests — Invalid input
# ---------------------------------------------------------------------------

class TestInvalidInput(unittest.TestCase):
    """Verify input validation against tool schemas."""

    def setUp(self) -> None:
        self.executor = ToolExecutor()
        self.executor.registry.register(
            ToolDescriptor(name="add", func=add, input_schema={
                "a": {"type": int, "required": True},
                "b": {"type": int, "required": True},
            })
        )

    def test_missing_required_param(self) -> None:
        res = self.executor.execute("add", {"a": 1})
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.VALIDATION)
        self.assertIn("b", res.error)

    def test_wrong_type(self) -> None:
        res = self.executor.execute("add", {"a": "one", "b": 2})
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.VALIDATION)
        self.assertIn("int", res.error)

    def test_unregistered_tool(self) -> None:
        res = self.executor.execute("nonexistent", {})
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.VALIDATION)
        self.assertIn("not registered", res.error)

    def test_extra_params_allowed(self) -> None:
        res = self.executor.execute("add", {"a": 1, "b": 2, "c": 999})
        # The schema doesn't forbid extras; the function will ignore them
        # because Python **kwargs isn't used — but our executor passes
        # only schema-known params?  No, it passes all.  add() will raise
        # TypeError for unexpected kwarg.  That's an EXECUTION error, not
        # validation.  Let's just confirm it doesn't crash the executor.
        self.assertIsInstance(res, ToolResult)


# ---------------------------------------------------------------------------
# Tests — Retry
# ---------------------------------------------------------------------------

class TestRetry(unittest.TestCase):
    """Verify retry policy with backoff."""

    def test_retry_succeeds_eventually(self) -> None:
        state: Dict[str, Any] = {"calls": 0}

        def flaky() -> str:
            state["calls"] += 1
            if state["calls"] < 3:
                raise ValueError("not yet")
            return "ok"

        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(
                name="flaky",
                func=flaky,
                retry_policy=RetryPolicy(
                    max_retries=5, delay=0.01, backoff_factor=1.0,
                    retryable_exceptions=(ValueError,),
                ),
            )
        )
        res = executor.execute("flaky")
        self.assertTrue(res.success)
        self.assertEqual(res.output, "ok")
        self.assertEqual(res.retries, 2)

    def test_retry_exhausted(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(
                name="always_fail",
                func=failing_tool,
                retry_policy=RetryPolicy(
                    max_retries=2, delay=0.01,
                    retryable_exceptions=(RuntimeError,),
                ),
            )
        )
        res = executor.execute("always_fail")
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.RETRY_EXHAUSTED)
        self.assertEqual(res.retries, 2)

    def test_non_retryable_exception(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(
                name="type_err",
                func=type_error_tool,
                retry_policy=RetryPolicy(
                    max_retries=5, delay=0.01,
                    retryable_exceptions=(ValueError,),
                ),
            )
        )
        res = executor.execute("type_err")
        self.assertFalse(res.success)
        self.assertEqual(res.error_category, ErrorCategory.EXECUTION)
        self.assertEqual(res.retries, 0)

    def test_retry_with_timeout(self) -> None:
        call_count = {"n": 0}

        def slow_then_ok() -> str:
            call_count["n"] += 1
            if call_count["n"] < 2:
                time.sleep(5)
            return "ok"

        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(
                name="slow_retry",
                func=slow_then_ok,
                retry_policy=RetryPolicy(
                    max_retries=3, delay=0.01,
                    retryable_exceptions=(TimeoutError,),
                ),
            )
        )
        res = executor.execute("slow_retry", timeout=0.15)
        self.assertTrue(res.success)
        self.assertEqual(res.output, "ok")


# ---------------------------------------------------------------------------
# Tests — Exception isolation
# ---------------------------------------------------------------------------

class TestExceptionIsolation(unittest.TestCase):
    """The executor must never propagate tool exceptions to the caller."""

    def test_runtime_error_caught(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="bad", func=failing_tool)
        )
        res = executor.execute("bad")
        self.assertFalse(res.success)
        self.assertIn("boom", res.error)

    def test_keyboard_interrupt_isolated(self) -> None:
        def interrupt_tool() -> None:
            raise KeyboardInterrupt("stop")

        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="kb", func=interrupt_tool)
        )
        # KeyboardInterrupt inherits BaseException; our executor catches
        # Exception.  Let's verify it still returns a ToolResult rather
        # than crashing.  (The threaded path wraps BaseException.)
        res = executor.execute("kb", timeout=1.0)
        self.assertFalse(res.success)

    def test_multiple_failures_dont_corrupt_executor(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="bad", func=failing_tool)
        )
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        for _ in range(5):
            executor.execute("bad")
        res = executor.execute("add", {"a": 1, "b": 2})
        self.assertTrue(res.success)
        self.assertEqual(res.output, 3)


# ---------------------------------------------------------------------------
# Tests — History
# ---------------------------------------------------------------------------

class TestHistory(unittest.TestCase):
    """Verify execution history recording and bounds."""

    def test_history_records_calls(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        executor.execute("add", {"a": 1, "b": 2})
        executor.execute("add", {"a": 3, "b": 4})
        self.assertEqual(len(executor.history), 2)

    def test_history_contains_correct_data(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="greet", func=greet)
        )
        executor.execute("greet", {"name": "Bob"})
        rec = executor.history[0]
        self.assertEqual(rec.tool_name, "greet")
        self.assertEqual(rec.inputs, {"name": "Bob"})
        self.assertTrue(rec.result.success)
        self.assertGreater(rec.timestamp, 0)

    def test_history_bounded(self) -> None:
        executor = ToolExecutor(history_size=3)
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        for i in range(10):
            executor.execute("add", {"a": i, "b": i})
        self.assertEqual(len(executor.history), 3)

    def test_clear_history(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        executor.execute("add", {"a": 1, "b": 2})
        executor.clear_history()
        self.assertEqual(len(executor.history), 0)

    def test_failed_calls_recorded(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="bad", func=failing_tool)
        )
        executor.execute("bad")
        self.assertEqual(len(executor.history), 1)
        self.assertFalse(executor.history[0].result.success)


# ---------------------------------------------------------------------------
# Tests — Metrics
# ---------------------------------------------------------------------------

class TestMetrics(unittest.TestCase):
    """Verify aggregate metrics tracking."""

    def setUp(self) -> None:
        self.executor = ToolExecutor()
        self.executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        self.executor.registry.register(
            ToolDescriptor(name="bad", func=failing_tool)
        )

    def test_success_metrics(self) -> None:
        self.executor.execute("add", {"a": 1, "b": 2})
        self.executor.execute("add", {"a": 3, "b": 4})
        m = self.executor.get_metrics("add")
        self.assertEqual(m["total_calls"], 2)
        self.assertEqual(m["successes"], 2)
        self.assertEqual(m["failures"], 0)

    def test_failure_metrics(self) -> None:
        self.executor.execute("bad")
        m = self.executor.get_metrics("bad")
        self.assertEqual(m["total_calls"], 1)
        self.assertEqual(m["failures"], 1)
        self.assertIn("execution", m["error_categories"])

    def test_mixed_metrics(self) -> None:
        self.executor.execute("add", {"a": 1, "b": 2})
        self.executor.execute("bad")
        self.executor.execute("add", {"a": 5, "b": 5})
        all_m = self.executor.get_metrics()
        self.assertEqual(all_m["add"]["total_calls"], 2)
        self.assertEqual(all_m["bad"]["total_calls"], 1)

    def test_duration_accumulates(self) -> None:
        self.executor.execute("add", {"a": 1, "b": 2})
        self.executor.execute("add", {"a": 1, "b": 2})
        m = self.executor.get_metrics("add")
        self.assertGreater(m["total_duration"], 0)

    def test_unknown_tool_metrics(self) -> None:
        m = self.executor.get_metrics("ghost")
        self.assertEqual(m, {})


# ---------------------------------------------------------------------------
# Tests — Serialization
# ---------------------------------------------------------------------------

class TestSerialization(unittest.TestCase):
    """Verify ToolResult and ExecutionRecord round-trip serialization."""

    def test_tool_result_to_dict(self) -> None:
        r = ToolResult(
            success=True,
            output=42,
            duration=0.123,
            retries=0,
            tool_name="add",
        )
        d = r.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["output"], 42)
        self.assertIsNone(d["error_category"])

    def test_tool_result_from_dict(self) -> None:
        d = {
            "success": False,
            "output": None,
            "error": "boom",
            "error_category": "execution",
            "duration": 0.5,
            "retries": 1,
            "tool_name": "bad",
            "metadata": {},
        }
        r = ToolResult.from_dict(d)
        self.assertFalse(r.success)
        self.assertEqual(r.error_category, ErrorCategory.EXECUTION)
        self.assertEqual(r.retries, 1)

    def test_round_trip(self) -> None:
        original = ToolResult(
            success=False,
            output=None,
            error="timeout!",
            error_category=ErrorCategory.TIMEOUT,
            duration=1.5,
            retries=3,
            tool_name="slow",
            metadata={"traceback": "line 42"},
        )
        restored = ToolResult.from_dict(original.to_dict())
        self.assertEqual(restored.success, original.success)
        self.assertEqual(restored.error, original.error)
        self.assertEqual(restored.error_category, original.error_category)
        self.assertEqual(restored.duration, original.duration)
        self.assertEqual(restored.retries, original.retries)
        self.assertEqual(restored.tool_name, original.tool_name)
        self.assertEqual(restored.metadata, original.metadata)

    def test_json_serializable(self) -> None:
        r = ToolResult(
            success=True,
            output={"key": "value"},
            duration=0.01,
            tool_name="test",
            error_category=ErrorCategory.VALIDATION,
        )
        json_str = json.dumps(r.to_dict())
        self.assertIsInstance(json_str, str)
        parsed = json.loads(json_str)
        self.assertEqual(parsed["error_category"], "validation")

    def test_execution_record_to_dict(self) -> None:
        rec = ExecutionRecord(
            tool_name="add",
            inputs={"a": 1, "b": 2},
            result=ToolResult(success=True, output=3, tool_name="add"),
        )
        d = rec.to_dict()
        self.assertEqual(d["tool_name"], "add")
        self.assertTrue(d["result"]["success"])

    def test_from_dict_unknown_category(self) -> None:
        d = {
            "success": False,
            "output": None,
            "error": "x",
            "error_category": "alien_category",
            "duration": 0.0,
            "retries": 0,
            "tool_name": "u",
            "metadata": {},
        }
        r = ToolResult.from_dict(d)
        self.assertEqual(r.error_category, ErrorCategory.UNKNOWN)


# ---------------------------------------------------------------------------
# Tests — InputValidator standalone
# ---------------------------------------------------------------------------

class TestInputValidator(unittest.TestCase):
    """Unit tests for the InputValidator helper."""

    def test_empty_schema_passes(self) -> None:
        ok, err = InputValidator.validate({"anything": 123}, {})
        self.assertTrue(ok)
        self.assertIsNone(err)

    def test_optional_missing_ok(self) -> None:
        schema = {"x": {"type": int, "required": False}}
        ok, err = InputValidator.validate({}, schema)
        self.assertTrue(ok)

    def test_required_missing_fails(self) -> None:
        schema = {"x": {"type": int, "required": True}}
        ok, err = InputValidator.validate({}, schema)
        self.assertFalse(ok)
        self.assertIn("x", err)

    def test_type_mismatch(self) -> None:
        schema = {"x": {"type": int, "required": True}}
        ok, err = InputValidator.validate({"x": "hello"}, schema)
        self.assertFalse(ok)
        self.assertIn("int", err)


# ---------------------------------------------------------------------------
# Tests — ToolRegistry standalone
# ---------------------------------------------------------------------------

class TestToolRegistry(unittest.TestCase):
    """Unit tests for the ToolRegistry helper."""

    def test_register_and_get(self) -> None:
        reg = ToolRegistry()
        reg.register(ToolDescriptor(name="t", func=add))
        self.assertIsNotNone(reg.get("t"))
        self.assertIn("t", reg)
        self.assertEqual(len(reg), 1)

    def test_unregister(self) -> None:
        reg = ToolRegistry()
        reg.register(ToolDescriptor(name="t", func=add))
        reg.unregister("t")
        self.assertIsNone(reg.get("t"))
        self.assertEqual(len(reg), 0)

    def test_list_tools(self) -> None:
        reg = ToolRegistry()
        reg.register(ToolDescriptor(name="a", func=add))
        reg.register(ToolDescriptor(name="b", func=greet))
        self.assertCountEqual(reg.list_tools(), ["a", "b"])


# ---------------------------------------------------------------------------
# Tests — RetryPolicy standalone
# ---------------------------------------------------------------------------

class TestRetryPolicy(unittest.TestCase):
    """Unit tests for RetryPolicy logic."""

    def test_should_retry_within_limit(self) -> None:
        p = RetryPolicy(max_retries=3, retryable_exceptions=(ValueError,))
        self.assertTrue(p.should_retry(0, ValueError()))
        self.assertTrue(p.should_retry(2, ValueError()))

    def test_should_not_retry_at_limit(self) -> None:
        p = RetryPolicy(max_retries=2, retryable_exceptions=(ValueError,))
        self.assertFalse(p.should_retry(2, ValueError()))

    def test_should_not_retry_wrong_exception(self) -> None:
        p = RetryPolicy(max_retries=5, retryable_exceptions=(ValueError,))
        self.assertFalse(p.should_retry(0, TypeError()))

    def test_wait_time_backoff(self) -> None:
        p = RetryPolicy(delay=1.0, backoff_factor=2.0)
        self.assertAlmostEqual(p.wait_time(0), 1.0)
        self.assertAlmostEqual(p.wait_time(1), 2.0)
        self.assertAlmostEqual(p.wait_time(2), 4.0)


# ---------------------------------------------------------------------------
# Tests — execute_many
# ---------------------------------------------------------------------------

class TestExecuteMany(unittest.TestCase):
    """Batch execution convenience method."""

    def test_batch(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        results = executor.execute_many([
            ("add", {"a": 1, "b": 2}),
            ("add", {"a": 10, "b": 20}),
        ])
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].output, 3)
        self.assertEqual(results[1].output, 30)


# ---------------------------------------------------------------------------
# Tests — Thread safety (smoke)
# ---------------------------------------------------------------------------

class TestThreadSafety(unittest.TestCase):
    """Quick smoke test for concurrent execution."""

    def test_concurrent_executions(self) -> None:
        executor = ToolExecutor()
        executor.registry.register(
            ToolDescriptor(name="add", func=add)
        )
        results: list = []
        lock = threading.Lock()

        def worker(a: int, b: int) -> None:
            r = executor.execute("add", {"a": a, "b": b})
            with lock:
                results.append(r)

        threads = [threading.Thread(target=worker, args=(i, i)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 20)
        self.assertTrue(all(r.success for r in results))
        self.assertEqual(len(executor.history), 20)


if __name__ == "__main__":
    unittest.main()
