"""Self Evolution Engine Orchestrator."""
import os
import sys
import json
import time
from typing import Dict, Any, List
from .config import PROJECT_ROOT, CANDIDATES_DIR
from .memory import EvolutionMemory
from .mapper import ProjectMapper
from .dependency_graph import DependencyGraph
from .detectors import ALL_DETECTORS
from .planner import ImprovementPlanner

class SelfEvolutionEngine:
    def __init__(self, project_dir: str = PROJECT_ROOT):
        self.project_dir = project_dir
        self.memory = EvolutionMemory()
        self.mapper = ProjectMapper()
        self.dep_builder = DependencyGraph()
        self.planner = ImprovementPlanner(self.memory)
        self._cycle_count = self.memory.get_metric("cycle_count", 0)

    def _make_result(self, status: str, success: bool, issues: List[Dict[str, Any]], start_time: float, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Guarantees every analysis result contains the required schema."""
        res = {
            "success": success,
            "duration_sec": round(time.time() - start_time, 4),
            "timestamp": time.time(),
            "analyzer": "SelfEvolutionEngine",
            "issues": issues,
            "status": status,
            "cycle": self._cycle_count
        }
        if extra:
            res.update(extra)
        return res

    def run_cycle(self) -> Dict[str, Any]:
        self._cycle_count += 1
        self.memory.update_metric("cycle_count", self._cycle_count)
        start = time.time()

        # 1. Inspect & Map
        file_map = self.mapper.inspect(self.project_dir)
        if not file_map:
            return self._make_result("empty_project", True, [], start)

        # 2. Build Dependencies
        dep_data = self.dep_builder.build(file_map)

        # 3. Run Detectors
        all_findings = []
        for DetectorClass in ALL_DETECTORS:
            detector = DetectorClass()
            try:
                findings = detector.detect(file_map, dep_data, self.memory)
                all_findings.extend(findings)
            except Exception as e:
                self.memory.record_attempt(detector.name, [], f"detector_crash: {e}", "failed")
                all_findings.append({"file": "", "line": 0, "severity": "high", "reason": f"Detector {detector.name} crashed: {e}", "category": detector.name})

        if not all_findings:
            self.memory.update_metric("last_cycle_findings", 0)
            return self._make_result("no_issues_found", True, [], start)

        # 4. Plan & Generate Candidates
        candidates = self.planner.plan(all_findings, file_map)
        saved_paths = []
        for cand in candidates:
            path = cand.save()
            saved_paths.append(path)
            self.memory.record_attempt(cand.finding_type, cand.affected_files, cand.reason, "proposed")

        self.memory.update_metric("last_cycle_findings", len(all_findings))
        self.memory.update_metric("last_cycle_candidates", len(candidates))

        return self._make_result(
            "completed",
            True,
            all_findings,
            start,
            {
                "files_inspected": len(file_map),
                "findings_count": len(all_findings),
                "candidates_generated": len(candidates),
                "candidate_paths": saved_paths
            }
        )

    def get_status(self) -> Dict[str, Any]:
        return self._make_result(
            "idle",
            True,
            [],
            time.time(),
            {
                "memory_stats": self.memory.get_stats(),
                "cycle_count": self._cycle_count,
                "candidates_dir": CANDIDATES_DIR
            }
        )

if __name__ == "__main__":
    engine = SelfEvolutionEngine()
    result = engine.run_cycle()
    print(json.dumps(result, indent=2))
