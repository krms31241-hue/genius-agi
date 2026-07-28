"""Improvement plan generation and candidate creation."""
import os
from typing import Dict, Any, List
from .candidate import CandidatePatch
from .memory import EvolutionMemory
from .config import MAX_CANDIDATES_PER_CYCLE, RISK_LEVELS

class ImprovementPlanner:
    def __init__(self, memory: EvolutionMemory):
        self.memory = memory

    def plan(self, findings: List[Dict[str, Any]], file_map: Dict[str, Dict[str, Any]]) -> List[CandidatePatch]:
        grouped = {}
        for f in findings:
            key = (f["category"], f["reason"])
            grouped.setdefault(key, []).append(f)

        candidates = []
        for (category, reason), items in grouped.items():
            files = list({i["file"] for i in items})
            if self.memory.is_known_failure(category, files, reason):
                continue

            max_sev = max(({"low": 1, "medium": 2, "high": 3}.get(i["severity"], 0) for i in items), default=0)
            risk = "high" if max_sev >= 3 else ("medium" if max_sev == 2 else "low")
            gain = min(1.0, len(files) * 0.15 + (0.2 if risk == "high" else 0.1))

            rollback = {}
            changes = {}
            for fpath in files:
                if fpath in file_map:
                    rollback[fpath] = file_map[fpath]["hash"]
                    changes[fpath] = self._generate_stub_fix(fpath, category, file_map[fpath]["content"])

            cand = CandidatePatch(
                finding_type=category,
                reason=reason,
                affected_files=files,
                risk_level=risk,
                estimated_gain=round(gain, 3),
                rollback_info=rollback,
                proposed_changes=changes
            )
            candidates.append(cand)

        candidates.sort(key=lambda c: c.estimated_gain, reverse=True)
        return candidates[:MAX_CANDIDATES_PER_CYCLE]

    def _generate_stub_fix(self, fpath: str, category: str, original: str) -> str:
        # Deterministic safe transformation stubs
        if category == "syntax":
            return original  # Syntax fixes require precise AST rewrite, deferred to lab
        if category == "crash_risk":
            return original.replace("except:", "except Exception:")
        if category == "logic":
            return original.replace("== True:", ":").replace("== False:", " is False:")
        if category == "security":
            return original.replace("eval(", "# eval disabled: ")
        return original
