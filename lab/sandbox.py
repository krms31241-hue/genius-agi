"""Virtual Sandbox: Isolated execution environment."""
import os
import sys
import subprocess
import tempfile
import shutil
import time
from typing import Dict, Any

class SandboxResult:
    def __init__(self, success: bool, exit_code: int, stdout: str, stderr: str,
                 duration: float, memory_mb: float, cpu_sec: float):
        self.success = success
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration = duration
        self.memory_mb = memory_mb
        self.cpu_sec = cpu_sec

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__.copy()

class VirtualSandbox:
    """Never executes inside the real project. All code runs in isolation."""
    def __init__(self, timeout_sec: float = 15.0, max_memory_mb: int = 256):
        self.timeout_sec = timeout_sec
        self.max_memory_mb = max_memory_mb

    def _setup_isolation(self, code_files: Dict[str, str]) -> str:
        temp_dir = tempfile.mkdtemp(prefix="autolab_sandbox_")
        for fname, content in code_files.items():
            fpath = os.path.join(temp_dir, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        return temp_dir

    def execute(self, code_files: Dict[str, str], entrypoint: str, args: list = None) -> SandboxResult:
        workdir = self._setup_isolation(code_files)
        env = os.environ.copy()
        env["PYTHONPATH"] = workdir
        env["SANDBOX_MODE"] = "1"
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [sys.executable, entrypoint] + (args or [])
        start = time.time()
        try:
            proc = subprocess.run(
                cmd, cwd=workdir, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=self.timeout_sec
            )
            duration = time.time() - start
            return SandboxResult(
                success=proc.returncode == 0,
                exit_code=proc.returncode,
                stdout=proc.stdout.decode("utf-8", errors="replace"),
                stderr=proc.stderr.decode("utf-8", errors="replace"),
                duration=duration,
                memory_mb=0.0,
                cpu_sec=duration
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(False, -1, "", "Sandbox timeout", self.timeout_sec, 0.0, self.timeout_sec)
        except Exception as e:
            return SandboxResult(False, -2, "", str(e), time.time() - start, 0.0, 0.0)
        finally:
            if workdir and os.path.exists(workdir):
                shutil.rmtree(workdir, ignore_errors=True)
