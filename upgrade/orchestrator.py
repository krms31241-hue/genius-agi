"""Automatic Upgrade Manager Orchestrator."""
import os
import sys
import time
import json
import threading
from typing import Dict, Any, Optional
from .resource_guard import ResourceGuard
from .crash_recovery import CrashRecovery
from .snapshot_manager import SnapshotManager
from .inspector import ProjectInspector
from .generator import PatchGenerator
from .benchmark import BenchmarkRunner
from .comparator import VersionComparator

# Import existing Code Laboratory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from lab.orchestrator import CodeLaboratory

class UpgradeManager:
    def __init__(self, project_dir: str, entrypoint: str, max_iterations: int = 3, cpu_limit_sec: float = 120.0, mem_limit_mb: int = 512):
        self.project_dir = os.path.abspath(project_dir)
        self.entrypoint = entrypoint
        self.max_iterations = max_iterations
        self.guard = ResourceGuard(max_cpu_sec=cpu_limit_sec, max_memory_mb=mem_limit_mb)
        self.recovery = CrashRecovery(os.path.join(self.project_dir, ".upgrade_state.json"))
        self.snapshots = SnapshotManager(os.path.join(self.project_dir, ".project_versions"))
        self.inspector = ProjectInspector()
        self.generator = PatchGenerator()
        self.benchmark = BenchmarkRunner()
        self.comparator = VersionComparator()
        self.lab = CodeLaboratory(timeout_sec=30.0, sandbox_timeout=15.0)
        self._evolution_lock = threading.Lock()
        self._consecutive_rejections = 0
        self._max_rejections = 3

    def run_upgrade_cycle(self) -> Dict[str, Any]:
        # Crash recovery check
        if self.recovery.is_interrupted():
            rec = self.recovery.get_recovery_action()
            if rec["action"] == "rollback" and rec.get("snap_id"):
                self.snapshots.rollback(rec["snap_id"], self.project_dir)
            self.recovery.clear()
            return {"status": "recovered", "action": "rolled_back_to_last_safe"}

        self.guard.apply_limits()
        try:
            return self._execute_pipeline()
        except Exception as e:
            self.recovery.save("crashed", error=str(e))
            return {"status": "crashed", "error": str(e), "recovery_state_saved": True}
        finally:
            self.guard.release_limits()

    def _execute_pipeline(self) -> Dict[str, Any]:
        self.guard.acquire_lock(self._evolution_lock, "upgrade_cycle", timeout=10.0)
        try:
            for iteration in range(1, self.max_iterations + 1):
                self.guard.check_cpu_time()
                if self._consecutive_rejections >= self._max_rejections:
                    return {"status": "halted", "reason": "max_consecutive_rejections_reached"}

                # 1. Inspect
                self.recovery.save("inspecting")
                inspection = self.inspector.inspect(self.project_dir)

                # 2. Generate improvement
                self.recovery.save("generating")
                candidate_files = self.generator.generate(inspection)
                if not candidate_files:
                    return {"status": "completed", "reason": "no_improvements_generated"}

                # 3. Create candidate patch & snapshot
                self.recovery.save("snapshotting")
                snap_id = self.snapshots.create_snapshot(self.project_dir)

                # 4. Run sandbox + validation + tests + security via Laboratory
                self.recovery.save("validating", snap_id=snap_id)
                lab_context = {"patch_id": f"upg_{iteration}", "requirements": inspection.get("dependencies", [])}
                lab_report = self.lab.validate_patch(candidate_files, self.entrypoint, lab_context)

                if not lab_report.get("passed"):
                    self._consecutive_rejections += 1
                    continue

                # 5. Apply candidate temporarily for benchmark
                self.recovery.save("benchmarking", snap_id=snap_id)
                temp_dir = self.project_dir + ".bench_tmp"
                import shutil
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                shutil.copytree(self.project_dir, temp_dir, ignore=shutil.ignore_patterns(".project_versions", ".git", "__pycache__"))
                for fpath, content in candidate_files.items():
                    target = os.path.join(temp_dir, fpath)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "w") as f:
                        f.write(content)

                baseline_metrics = self.benchmark.run(self.project_dir, self.entrypoint)
                candidate_metrics = self.benchmark.run(temp_dir, self.entrypoint)
                shutil.rmtree(temp_dir, ignore_errors=True)

                # 6. Compare
                self.recovery.save("comparing", snap_id=snap_id)
                comparison = self.comparator.compare(baseline_metrics, candidate_metrics, lab_report)

                if comparison["decision"] == "REJECT":
                    self._consecutive_rejections += 1
                    self.recovery.save("rejected", snap_id=snap_id)
                    continue

                # 7. Approve: Archive, Activate, Store Learning
                self.recovery.save("activating", snap_id=snap_id)
                self.snapshots.archive_current(self.project_dir)
                # Write candidate files to project
                for fpath, content in candidate_files.items():
                    target = os.path.join(self.project_dir, fpath)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with open(target, "w") as f:
                        f.write(content)

                self.recovery.save("completed")
                self._consecutive_rejections = 0
                return {
                    "status": "upgraded",
                    "iteration": iteration,
                    "snap_id": snap_id,
                    "comparison": comparison,
                    "lab_report": lab_report
                }

            return {"status": "completed", "reason": "max_iterations_reached"}
        finally:
            self.guard.release_lock(self._evolution_lock, "upgrade_cycle")
