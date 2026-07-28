"""CPU/Memory limits, recursion & deadlock detection."""
import os
import sys
import time
import threading
import resource
from typing import Optional

class ResourceGuard:
    def __init__(self, max_cpu_sec: float = 60.0, max_memory_mb: int = 512, max_recursion_depth: int = 500):
        self.max_cpu_sec = max_cpu_sec
        self.max_memory_mb = max_memory_mb
        self.max_recursion_depth = max_recursion_depth
        self._start_time = time.time()
        self._lock_registry = {}
        self._original_recursion_limit = sys.getrecursionlimit()

    def apply_limits(self):
        sys.setrecursionlimit(self.max_recursion_depth)
        mem_bytes = self.max_memory_mb * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (int(self.max_cpu_sec), int(self.max_cpu_sec) + 5))
        except Exception:
            pass

    def release_limits(self):
        sys.setrecursionlimit(self._original_recursion_limit)
        try:
            resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
            resource.setrlimit(resource.RLIMIT_CPU, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        except Exception:
            pass

    def check_cpu_time(self):
        elapsed = time.time() - self._start_time
        if elapsed > self.max_cpu_sec:
            raise TimeoutError(f"CPU time limit exceeded: {elapsed:.2f}s > {self.max_cpu_sec}s")

    def acquire_lock(self, lock: threading.Lock, name: str, timeout: float = 5.0) -> bool:
        acquired = lock.acquire(timeout=timeout)
        if not acquired:
            raise RuntimeError(f"Deadlock detected: Failed to acquire lock '{name}' within {timeout}s")
        self._lock_registry[name] = time.time()
        return True

    def release_lock(self, lock: threading.Lock, name: str):
        try:
            lock.release()
        except RuntimeError:
            pass
        self._lock_registry.pop(name, None)

    def reset_timer(self):
        self._start_time = time.time()
