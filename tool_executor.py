"""
tool_executor.py — Genius-AGI Tool Execution Engine

Features:
  - Execute registered tools
  - Validate inputs against tool schemas
  - Capture outputs (stdout, return values)
  - Timeout support via threading
  - Configurable retry policy with exponential backoff
  - Exception isolation (tools cannot crash the executor)
  - Structured ToolResult with rich metadata
  - Execution history with bounded buffer
  - Duration measurement (wall-clock)
  - Error categorization for downstream handling
"""

from __future__ import annotations

import enum
import time
import threading
import traceback
import logging
from dataclasses import dataclass, field, asdict
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)
from collections import deque
from copy import deepcopy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error categorization
# ---------------------------------------------------------------------------

class ErrorCategory(str, enum.Enum):
    """Coarse-grained error buckets for downstream routing."""
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    EXECUTION = "execution"
    RETRY_EXHAUSTED = "retry_exhausted"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Structured result
# ---------------------------------------------------------------------------

@dataclass
class ToolResult:
    """Immutable-ish value object returned after every tool invocation."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    duration: float = 0.0
    retries: int = 0
    tool_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    # -- serialization helpers -----------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        d = asdict(self)
        if d.get("error_category") is not None:
            d["error_category"] = d["error_category"].value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolResult":
        """Reconstruct a ToolResult from a plain dict."""
        data = dict(data)
        cat = data.get("error_category")
        if isinstance(cat, str):
            try:
                data["error_category"] = ErrorCategory(cat)
            except ValueError:
                data["error_category"] = ErrorCategory.UNKNOWN
        return cls(**data)

    def __repr__(self) -> str:
        status = "OK" if self.success else "FAIL"
        return (
            f"ToolResult({status}, tool={self.tool_name!r}, "
            f"dur={self.duration:.4f}s, retries={self.retries})"
        )


# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

@dataclass
class RetryPolicy:
    """Controls how the executor retries failed invocations."""
    max_retries: int = 0
    delay: float = 0.0
    backoff_factor: float = 1.0
    retryable_exceptions: Tuple[Type[BaseException], ...] = (Exception,)

    def should_retry(self, attempt: int, exc: BaseException) -> bool:
        if attempt >= self.max_retries:
            return False
        return isinstance(exc, self.retryable_exceptions)

    def wait_time(self, attempt: int) -> float:
        return self.delay * (self.backoff_factor ** attempt)


# ---------------------------------------------------------------------------
# Execution history record
# ---------------------------------------------------------------------------

@dataclass
class ExecutionRecord:
    """One entry in the execution history log."""
    tool_name: str
    inputs: Dict[str, Any]
    result: ToolResult
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "inputs": self.inputs,
            "result": self.result.to_dict(),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Tool descriptor (lightweight registry entry)
# ---------------------------------------------------------------------------

@dataclass
class ToolDescriptor:
    """Describes a single callable tool the executor can invoke."""
    name: str
    func: Callable[..., Any]
    description: str = ""
    input_schema: Optional[Dict[str, Any]] = None  # simple type map
    timeout: Optional[float] = None
    retry_policy: Optional[RetryPolicy] = None

    def __post_init__(self) -> None:
        if self.input_schema is None:
            self.input_schema = {}
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()


# ---------------------------------------------------------------------------
# Tool registry (thin wrapper — compatible with external registries)
# ---------------------------------------------------------------------------

class ToolRegistry:
    """In-memory registry of ToolDescriptors."""

    def __init__(self) -> None:
        self._tools: Dict[str, ToolDescriptor] = {}

    def register(self, descriptor: ToolDescriptor) -> None:
        self._tools[descriptor.name] = descriptor

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[ToolDescriptor]:
        return self._tools.get(name)

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# ---------------------------------------------------------------------------
# Input validator (simple schema-based)
# ---------------------------------------------------------------------------

class InputValidator:
    """
    Validates tool inputs against a simple schema.

    Schema format (dict):
        {
            "param_name": {"type": <python_type>, "required": True/False},
            ...
        }

    If the schema is empty, all inputs are accepted.
    """

    @staticmethod
    def validate(
        inputs: Dict[str, Any],
        schema: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        if not schema:
            return True, None

        for param, rules in schema.items():
            required = rules.get("required", False)
            expected_type = rules.get("type")

            if param not in inputs:
                if required:
                    return False, f"Missing required parameter: '{param}'"
                continue

            value = inputs[param]
            if expected_type is not None and not isinstance(value, expected_type):
                return (
                    False,
                    f"Parameter '{param}' expected type "
                    f"{expected_type.__name__}, got {type(value).__name__}",
                )

        return True, None


# ---------------------------------------------------------------------------
# Main executor
# ---------------------------------------------------------------------------

class ToolExecutor:
    """
    Central execution engine for Genius-AGI tools.

    Parameters
    ----------
    registry : ToolRegistry | None
        Pre-populated registry.  A fresh one is created when *None*.
    default_timeout : float | None
        Fallback timeout (seconds) when a tool has no per-tool timeout.
    default_retry : RetryPolicy | None
        Fallback retry policy.
    history_size : int
        Maximum number of ExecutionRecords kept in memory.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        default_timeout: Optional[float] = None,
        default_retry: Optional[RetryPolicy] = None,
        history_size: int = 1000,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.default_timeout = default_timeout
        self.default_retry = default_retry or RetryPolicy()
        self._history: deque[ExecutionRecord] = deque(maxlen=history_size)
        self._lock = threading.Lock()

        # Aggregate metrics
        self._metrics: Dict[str, Dict[str, Any]] = {}

    # -- public API ----------------------------------------------------------

    def execute(
        self,
        tool_name: str,
        inputs: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> ToolResult:
        """
        Execute *tool_name* with *inputs* and return a structured ToolResult.

        The method never raises — all exceptions are caught and wrapped.
        """
        if inputs is None:
            inputs = {}

        start = time.monotonic()

        # 1. Look up tool
        descriptor = self.registry.get(tool_name)
        if descriptor is None:
            result = ToolResult(
                success=False,
                error=f"Tool '{tool_name}' is not registered.",
                error_category=ErrorCategory.VALIDATION,
                tool_name=tool_name,
                duration=time.monotonic() - start,
            )
            self._record(tool_name, inputs, result)
            return result

        # 2. Validate inputs
        ok, err_msg = InputValidator.validate(inputs, descriptor.input_schema)
        if not ok:
            result = ToolResult(
                success=False,
                error=err_msg,
                error_category=ErrorCategory.VALIDATION,
                tool_name=tool_name,
                duration=time.monotonic() - start,
            )
            self._record(tool_name, inputs, result)
            return result

        # 3. Resolve timeout & retry
        effective_timeout = (
            timeout
            if timeout is not None
            else descriptor.timeout
            if descriptor.timeout is not None
            else self.default_timeout
        )
        effective_retry = (
            retry_policy
            if retry_policy is not None
            else descriptor.retry_policy
            if descriptor.retry_policy and descriptor.retry_policy.max_retries > 0
            else self.default_retry
        )

        # 4. Execute with retry + timeout + isolation
        attempt = 0
        last_exc: Optional[BaseException] = None
        output: Any = None
        success = False

        while True:
            try:
                output = self._run_with_timeout(
                    descriptor.func, inputs, effective_timeout
                )
                success = True
                break
            except TimeoutError as exc:
                last_exc = exc
                if not effective_retry.should_retry(attempt, exc):
                    break
                self._retry_sleep(effective_retry, attempt)
                attempt += 1
            except Exception as exc:
                last_exc = exc
                if not effective_retry.should_retry(attempt, exc):
                    break
                self._retry_sleep(effective_retry, attempt)
                attempt += 1

        duration = time.monotonic() - start

        # 5. Build result
        if success:
            result = ToolResult(
                success=True,
                output=output,
                duration=duration,
                retries=attempt,
                tool_name=tool_name,
            )
        else:
            category = self._categorize(last_exc, attempt, effective_retry)
            result = ToolResult(
                success=False,
                error=str(last_exc),
                error_category=category,
                duration=duration,
                retries=attempt,
                tool_name=tool_name,
                metadata={"traceback": traceback.format_exc()},
            )

        self._record(tool_name, inputs, result)
        return result

    # -- convenience wrappers ------------------------------------------------

    def execute_many(
        self,
        calls: Sequence[Tuple[str, Dict[str, Any]]],
    ) -> List[ToolResult]:
        """Execute a batch of (tool_name, inputs) pairs sequentially."""
        return [self.execute(name, inp) for name, inp in calls]

    # -- history & metrics ---------------------------------------------------

    @property
    def history(self) -> List[ExecutionRecord]:
        with self._lock:
            return list(self._history)

    def clear_history(self) -> None:
        with self._lock:
            self._history.clear()

    def get_metrics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Return aggregate execution metrics.

        If *tool_name* is given, return metrics for that tool only.
        """
        with self._lock:
            if tool_name:
                return dict(self._metrics.get(tool_name, {}))
            return {k: dict(v) for k, v in self._metrics.items()}

    # -- internal helpers ----------------------------------------------------

    def _run_with_timeout(
        self,
        func: Callable[..., Any],
        inputs: Dict[str, Any],
        timeout: Optional[float],
    ) -> Any:
        """Run *func(**inputs)*, raising TimeoutError if it exceeds *timeout*."""
        if timeout is None or timeout <= 0:
            return func(**inputs)

        result_holder: Dict[str, Any] = {}
        exc_holder: Dict[str, BaseException] = {}

        def target() -> None:
            try:
                result_holder["value"] = func(**inputs)
            except BaseException as e:
                exc_holder["exc"] = e

        t = threading.Thread(target=target, daemon=True)
        t.start()
        t.join(timeout=timeout)

        if t.is_alive():
            raise TimeoutError(
                f"Tool execution exceeded {timeout}s timeout."
            )

        if "exc" in exc_holder:
            exc = exc_holder["exc"]
            if isinstance(exc, KeyboardInterrupt):
                raise RuntimeError(str(exc))
            raise exc

        return result_holder.get("value")

    @staticmethod
    def _retry_sleep(policy: RetryPolicy, attempt: int) -> None:
        wait = policy.wait_time(attempt)
        if wait > 0:
            time.sleep(wait)

    @staticmethod
    def _categorize(
        exc: Optional[BaseException],
        attempts: int,
        policy: RetryPolicy,
    ) -> ErrorCategory:
        if exc is None:
            return ErrorCategory.UNKNOWN
        if isinstance(exc, TimeoutError):
            if attempts >= policy.max_retries and policy.max_retries > 0:
                return ErrorCategory.RETRY_EXHAUSTED
            return ErrorCategory.TIMEOUT
        if attempts >= policy.max_retries and policy.max_retries > 0:
            return ErrorCategory.RETRY_EXHAUSTED
        return ErrorCategory.EXECUTION

    def _record(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        result: ToolResult,
    ) -> None:
        with self._lock:
            record = ExecutionRecord(
                tool_name=tool_name,
                inputs=deepcopy(inputs),
                result=result,
            )
            self._history.append(record)
            self._update_metrics(tool_name, result)

    def _update_metrics(self, tool_name: str, result: ToolResult) -> None:
        if tool_name not in self._metrics:
            self._metrics[tool_name] = {
                "total_calls": 0,
                "successes": 0,
                "failures": 0,
                "total_duration": 0.0,
                "total_retries": 0,
                "error_categories": {},
            }
        m = self._metrics[tool_name]
        m["total_calls"] += 1
        if result.success:
            m["successes"] += 1
        else:
            m["failures"] += 1
            cat = result.error_category.value if result.error_category else "unknown"
            m["error_categories"][cat] = m["error_categories"].get(cat, 0) + 1
        m["total_duration"] += result.duration
        m["total_retries"] += result.retries
