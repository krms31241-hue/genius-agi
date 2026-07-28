"""Main Laboratory Orchestrator."""
import os
import sys
import json
import time
from typing import Dict, Any
from .watchdog import Watchdog, WatchdogTimeout
from .sandbox import VirtualSandbox
from .failure_db import FailureDB
from .reporter import LabReporter
from .rollback import RollbackManager
from .analyzers import ALL_ANALYZERS

class CodeLaboratory:
    def __init__(self, timeout_sec: float = 30.0, sandbox_timeout: float = 15.0):
        self.timeout_sec = timeout_sec
        self.sandbox = VirtualSandbox(timeout_sec=sandbox_timeout)
        self.failure_db = FailureDB()
        self.reporter = LabReporter()
        self.rollback = RollbackManager()
        self.watchdog = Watchdog(timeout_sec=timeout_sec)

    def validate_patch(self, patch_files: Dict[str, str], entrypoint: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        context = context or {}
        patch_id = context.get("patch_id", f"patch_{int(time.time())}")
        combined_code = "\n".join(patch_files.values())

        # Adaptive failure checking
        known = self.failure_db.is_known_failure(combined_code)
        revalidating = False
        if known:
            category = known.get("category", "runtime")
            if category in FailureDB.PERMANENT_CATEGORIES:
                return {"passed": False, "rejected": True, "reason": "Permanently blocked failure pattern", "details": known, "scores": {}}
            else:
                # Transient failure: allow ONE fresh validation cycle
                revalidating = True

        snap_id = self.rollback.snapshot(patch_files)

        try:
            def _pipeline():
                analyzer_results = []
                for AnalyzerClass in ALL_ANALYZERS:
                    analyzer = AnalyzerClass()
                    res = analyzer.analyze(combined_code, list(patch_files.keys())[0], context)
                    res["analyzer"] = analyzer.name
                    analyzer_results.append(res)
                    if not res["passed"] and analyzer.name in ("syntax", "security", "circular_dependencies"):
                        return {"analyzer_results": analyzer_results, "sandbox_result": None, "early_exit": True}

                sandbox_res = self.sandbox.execute(patch_files, entrypoint)
                return {"analyzer_results": analyzer_results, "sandbox_result": sandbox_res.to_dict(), "early_exit": False}

            result = self.watchdog.run(_pipeline)

            sandbox_ok = result.get("sandbox_result") and result["sandbox_result"].get("success", False)

            if result.get("early_exit") or not sandbox_ok:
                reason = "Static analysis failure" if result.get("early_exit") else "Sandbox execution failed"
                cat = "security" if result.get("early_exit") else "sandbox"
                self.failure_db.learn_and_block(combined_code, reason, json.dumps(result), category=cat)
                report = self.reporter.generate(result["analyzer_results"], result.get("sandbox_result") or {}, patch_id)
                report["passed"] = False
                report["rejected"] = True
                report["reason"] = reason
                self.reporter.save(report, f"lab_report_{patch_id}.json")
                return report

            # Success path
            if revalidating:
                # Proven fixed: adaptively forget the obsolete failure
                self.failure_db.unblock_failure(combined_code)

            report = self.reporter.generate(result["analyzer_results"], result["sandbox_result"], patch_id)
            report["passed"] = True
            report["snap_id"] = snap_id
            self.reporter.save(report, f"lab_report_{patch_id}.json")
            return report

        except WatchdogTimeout as e:
            self.failure_db.learn_and_block(combined_code, "timeout", str(e), category="timeout")
            return {"passed": False, "rejected": True, "reason": "Watchdog timeout", "details": str(e), "scores": {}}
        except Exception as e:
            self.failure_db.learn_and_block(combined_code, "runtime_error", str(e), category="runtime")
            return {"passed": False, "rejected": True, "reason": "Laboratory error", "details": str(e), "scores": {}}
        finally:
            self.rollback.cleanup_old()
