"""Performance benchmarking and comparison."""
import os
import sys
import time
import subprocess
import resource
from typing import Dict, Any, Optional

class BenchmarkRunner:
    def run(self, project_dir: str, entrypoint: str, timeout_sec: float = 30.0) -> Dict[str, Any]:
        env = os.environ.copy()
        env["PYTHONPATH"] = project_dir
        start = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, entrypoint],
                cwd=project_dir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=timeout_sec
            )
            duration = time.time() - start
            mem_mb = 0.0
            try:
                import psutil
                p = psutil.Process(proc.pid)
                mem_mb = p.memory_info().rss / (1024 * 1024)
            except Exception:
                try:
                    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
                    mem_mb = usage.ru_maxrss / 1024
                except Exception:
                    pass
            return {
                "success": proc.returncode == 0,
                "duration_sec": round(duration, 4),
                "memory_mb": round(mem_mb, 2),
                "exit_code": proc.returncode,
                "stdout": proc.stdout.decode("utf-8", errors="replace")[:500],
                "stderr": proc.stderr.decode("utf-8", errors="replace")[:500]
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "duration_sec": timeout_sec, "memory_mb": 0.0, "exit_code": -1, "stdout": "", "stderr": "Timeout"}
        except Exception as e:
            return {"success": False, "duration_sec": 0.0, "memory_mb": 0.0, "exit_code": -2, "stdout": "", "stderr": str(e)}
