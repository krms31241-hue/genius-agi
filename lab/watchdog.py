"""Watchdog, timeout protection, and emergency shutdown."""
import concurrent.futures
import os
import shutil
from typing import Callable, Any

class WatchdogTimeout(Exception):
    pass

class Watchdog:
    """Hard timeout guardian with clean termination and no background thread crashes."""
    def __init__(self, timeout_sec: float = 30.0, cleanup_dirs: list = None):
        self.timeout_sec = timeout_sec
        self.cleanup_dirs = cleanup_dirs or []

    def _emergency_shutdown(self):
        for d in self.cleanup_dirs:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d, ignore_errors=True)
                except Exception:
                    pass

    def run(self, func: Callable, *args, **kwargs) -> Any:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(func, *args, **kwargs)
            try:
                return future.result(timeout=self.timeout_sec)
            except concurrent.futures.TimeoutError:
                self._emergency_shutdown()
                raise WatchdogTimeout(f"Execution exceeded {self.timeout_sec}s limit. Clean shutdown triggered.")
            except Exception as e:
                future.cancel()
                raise
