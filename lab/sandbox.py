"""
lab/sandbox.py

Secure subprocess sandbox for the AGI lab runtime.

This module replaces the previous execution engine with a real secure
sandbox built on subprocess.Popen. It enforces execution timeouts,
captures stdout/stderr with bounded size, reports exit code and
duration, monitors memory and CPU usage, and guarantees cleanup of
child processes on timeout or failure.

The implementation reuses lab.watchdog.Watchdog and
upgrade.resource_guard.ResourceGuard when they are available, so no
logic is duplicated.
"""

from __future__ import annotations

import os
import sys
import time
import shlex
import signal
import shutil
import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

# ---------------------------------------------------------------------------
# Optional reuse of existing project modules.
# We import defensively so that sandbox remains functional even if those
# modules are unavailable in a particular deployment.
# ---------------------------------------------------------------------------
try:
    from lab.watchdog import Watchdog  # type: ignore
except Exception:  # pragma: no cover - defensive
    Watchdog = None  # type: ignore

try:
    from upgrade.resource_guard import ResourceGuard  # type: ignore
except Exception:  # pragma: no cover - defensive
    ResourceGuard = None  # type: ignore

try:
    import psutil as _psutil  # type: ignore
except Exception:  # pragma: no cover - defensive
    _psutil = None  # type: ignore


# ---------------------------------------------------------------------------
# Result container.
# We expose both attribute access and dict-like access so that callers
# written against either the previous object-style or dict-style API
# continue to work unchanged.
# ---------------------------------------------------------------------------
@dataclass
class ExecutionResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    duration: float = 0.0
    timed_out: bool = False
    killed: bool = False
    peak_memory_bytes: int = 0
    peak_cpu_percent: float = 0.0
    truncated: bool = False
    pid: Optional[int] = None
    command: Tuple[str, ...] = ()

    # Dict-like access for backward compatibility with callers that
    # treated the previous result as a mapping.
    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def keys(self) -> List[str]:
        return [
            "stdout", "stderr", "exit_code", "duration", "timed_out",
            "killed", "peak_memory_bytes", "peak_cpu_percent",
            "truncated", "pid", "command",
        ]

    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]

    def values(self):
        return [getattr(self, k) for k in self.keys()]

    def as_dict(self) -> Dict[str, Any]:
        return dict(self.items())

    # Backward compatibility with the old sandbox API
    def to_dict(self) -> Dict[str, Any]:
        return self.as_dict()


# ---------------------------------------------------------------------------
# Sandbox.
# ---------------------------------------------------------------------------
class Sandbox:
    """Secure subprocess sandbox.

    The public surface is intentionally small and stable:
      * Sandbox(timeout=..., max_output=..., memory_limit=..., cpu_limit=...)
      * sandbox.run(command, cwd=None, env=None, input=None) -> ExecutionResult
      * sandbox.execute(...)  -- alias kept for backward compatibility
    """

    DEFAULT_TIMEOUT: float = 30.0
    DEFAULT_MAX_OUTPUT: int = 1 * 1024 * 1024  # 1 MiB per stream

    def __init__(
        self,
        timeout: Optional[float] = None,
        max_output: Optional[int] = None,
        memory_limit: Optional[int] = None,
        cpu_limit: Optional[float] = None,
        allowed_executables: Optional[Sequence[str]] = None,
    ) -> None:
        self.timeout = self.DEFAULT_TIMEOUT if timeout is None else float(timeout)
        self.max_output = (
            self.DEFAULT_MAX_OUTPUT if max_output is None else int(max_output)
        )
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.allowed_executables = (
            tuple(allowed_executables) if allowed_executables else None
        )

        # Reuse existing project components instead of duplicating logic.
        self._watchdog = Watchdog() if Watchdog is not None else None
        self._resource_guard = ResourceGuard() if ResourceGuard is not None else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def run(
        self,
        command: Union[str, Sequence[str]],
        cwd: Optional[str] = None,
        env: Optional[Mapping[str, str]] = None,
        input: Optional[Union[str, bytes]] = None,  # noqa: A002 (shadow builtin)
    ) -> ExecutionResult:
        args = self._normalize_command(command)
        run_env = self._build_env(env)
        preexec = self._build_preexec()

        result = ExecutionResult(command=tuple(args))
        start = time.monotonic()

        if self._watchdog is not None and hasattr(self._watchdog, "start"):
            try:
                self._watchdog.start()
            except Exception:
                pass

        proc: Optional[subprocess.Popen] = None
        monitor: Optional[Tuple[threading.Thread, Dict[str, Any]]] = None
        try:
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE if input is not None else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=run_env,
                preexec_fn=preexec,
                start_new_session=self._supports_session(),
                shell=False,  # hard requirement: never use shell=True
            )
            result.pid = proc.pid

            monitor = self._start_resource_monitor(proc)

            stdin_bytes = self._encode_input(input)
            try:
                stdout_b, stderr_b = proc.communicate(
                    input=stdin_bytes, timeout=self.timeout
                )
                result.exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                result.timed_out = True
                result.killed = True
                self._kill_process_tree(proc)
                stdout_b, stderr_b = proc.communicate()
                result.exit_code = proc.returncode

            (
                result.stdout,
                result.stderr,
                result.truncated,
            ) = self._decode_and_truncate(stdout_b or b"", stderr_b or b"")

        except FileNotFoundError as exc:
            result.stderr = f"sandbox: executable not found: {exc}"
            result.exit_code = 127
        except OSError as exc:
            result.stderr = f"sandbox: os error: {exc}"
            result.exit_code = 126
        except Exception as exc:  # defensive: never leak
            result.stderr = f"sandbox: internal error: {exc}"
            result.exit_code = 125
        finally:
            if monitor is not None:
                peak_mem, peak_cpu = self._stop_resource_monitor(monitor)
                result.peak_memory_bytes = peak_mem
                result.peak_cpu_percent = peak_cpu
            if proc is not None:
                # Belt-and-suspenders cleanup.
                self._kill_process_tree(proc)
            if self._watchdog is not None and hasattr(self._watchdog, "stop"):
                try:
                    self._watchdog.stop()
                except Exception:
                    pass
            result.duration = time.monotonic() - start

        return result

    # Backward-compatible alias.
    def execute(self, patch_files, entrypoint):
        """
        Backward-compatible API expected by CodeLaboratory.
        """

        import tempfile
        import os
        import sys

        with tempfile.TemporaryDirectory() as tmpdir:

            for name, content in patch_files.items():
                filepath = os.path.join(tmpdir, name)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)

            target = os.path.join(tmpdir, entrypoint)

            result = self.run(
                [sys.executable, target],
                cwd=tmpdir,
            )

            data = result.as_dict()
            data["success"] = (
                (not result.timed_out)
                and (result.exit_code == 0)
            )

            return data

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _normalize_command(self, command: Union[str, Sequence[str]]) -> List[str]:
        if isinstance(command, str):
            args = shlex.split(command)
        else:
            args = [str(x) for x in command]
        if not args:
            raise ValueError("sandbox: empty command")
        if self.allowed_executables is not None:
            exe = args[0]
            resolved = shutil.which(exe) or exe
            if resolved not in self.allowed_executables and exe not in self.allowed_executables:
                raise ValueError(
                    f"sandbox: executable not permitted: {exe}"
                )
        return args

    def _build_env(self, env: Optional[Mapping[str, str]]) -> Optional[Dict[str, str]]:
        if env is None:
            return None  # inherit parent environment
        merged = os.environ.copy()
        merged.update({str(k): str(v) for k, v in env.items()})
        return merged

    def _build_preexec(self):
        # Delegate resource-limit setup to ResourceGuard if available.
        if self._resource_guard is not None and hasattr(
            self._resource_guard, "preexec_fn"
        ):
            try:
                return self._resource_guard.preexec_fn(
                    memory_limit=self.memory_limit,
                    cpu_limit=self.cpu_limit,
                )
            except Exception:
                return None
        return None

    @staticmethod
    def _supports_session() -> bool:
        return os.name != "nt"

    @staticmethod
    def _encode_input(input: Optional[Union[str, bytes]]) -> Optional[bytes]:
        if input is None:
            return None
        if isinstance(input, bytes):
            return input
        return input.encode("utf-8")

    def _decode_and_truncate(
        self, stdout_b: bytes, stderr_b: bytes
    ) -> Tuple[str, str, bool]:
        truncated = False

        def _limit(data: bytes) -> bytes:
            nonlocal truncated
            if len(data) > self.max_output:
                truncated = True
                return data[: self.max_output]
            return data

        def _decode(data: bytes) -> str:
            try:
                return data.decode("utf-8", errors="replace")
            except Exception:
                return data.decode("latin-1", errors="replace")

        return _decode(_limit(stdout_b)), _decode(_limit(stderr_b)), truncated

    # ------------------------------------------------------------------
    # Process-tree termination.
    # ------------------------------------------------------------------
    def _kill_process_tree(self, proc: subprocess.Popen) -> None:
        if proc is None:
            return
        try:
            if proc.poll() is not None:
                return
        except Exception:
            pass

        # Prefer psutil for reliable recursive kill.
        if _psutil is not None:
            try:
                parent = _psutil.Process(proc.pid)
                children = parent.children(recursive=True)
                for c in children:
                    try:
                        c.kill()
                    except _psutil.NoSuchProcess:
                        pass
                try:
                    parent.kill()
                except _psutil.NoSuchProcess:
                    pass
                # Wait briefly for termination.
                _psutil.wait_procs(children + [parent], timeout=2.0)
                return
            except _psutil.NoSuchProcess:
                return
            except Exception:
                pass  # fall through to OS-level fallback

        # OS-level fallback: process group kill on POSIX, then direct kill.
        try:
            if os.name != "nt":
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=2.0)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Resource monitoring.
    # ------------------------------------------------------------------
    def _start_resource_monitor(
        self, proc: subprocess.Popen
    ) -> Tuple[threading.Thread, Dict[str, Any]]:
        state: Dict[str, Any] = {"peak_mem": 0, "peak_cpu": 0.0, "stop": False}

        def _loop() -> None:
            while not state["stop"]:
                try:
                    if _psutil is not None and _psutil.pid_exists(proc.pid):
                        parent = _psutil.Process(proc.pid)
                        mem = parent.memory_info().rss
                        try:
                            cpu = parent.cpu_percent(interval=None)
                        except Exception:
                            cpu = 0.0
                        for child in parent.children(recursive=True):
                            try:
                                mem += child.memory_info().rss
                                cpu += child.cpu_percent(interval=None)
                            except (_psutil.NoSuchProcess, _psutil.AccessDenied):
                                pass
                        if mem > state["peak_mem"]:
                            state["peak_mem"] = mem
                        if cpu > state["peak_cpu"]:
                            state["peak_cpu"] = cpu
                    else:
                        # /proc fallback (Linux only) when psutil is absent.
                        try:
                            if os.name == "posix":
                                status_path = f"/proc/{proc.pid}/status"
                                if os.path.exists(status_path):
                                    with open(status_path, "r") as fh:
                                        for line in fh:
                                            if line.startswith("VmRSS:"):
                                                kb = int(
                                                    line.split()[1]
                                                )
                                                b = kb * 1024
                                                if b > state["peak_mem"]:
                                                    state["peak_mem"] = b
                                                break
                        except Exception:
                            pass
                except Exception:
                    pass
                time.sleep(0.1)

        t = threading.Thread(target=_loop, name="sandbox-monitor", daemon=True)
        t.start()
        return t, state

    @staticmethod
    def _stop_resource_monitor(
        monitor: Tuple[threading.Thread, Dict[str, Any]]
    ) -> Tuple[int, float]:
        t, state = monitor
        state["stop"] = True
        t.join(timeout=1.0)
        return int(state.get("peak_mem", 0)), float(state.get("peak_cpu", 0.0))


# ---------------------------------------------------------------------------
# Module-level convenience function. Kept for callers that used the
# previous functional interface.
# ---------------------------------------------------------------------------
_default_sandbox = Sandbox()


def run(
    command: Union[str, Sequence[str]],
    timeout: Optional[float] = None,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    input: Optional[Union[str, bytes]] = None,  # noqa: A002
    max_output: Optional[int] = None,
) -> ExecutionResult:
    sandbox = Sandbox(timeout=timeout, max_output=max_output)
    return sandbox.run(command, cwd=cwd, env=env, input=input)

# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------


class VirtualSandbox(Sandbox):
    """
    Backward-compatible wrapper for the legacy API.
    """
    def __init__(self, timeout_sec=30.0, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout_sec
        super().__init__(**kwargs)

