"""Version comparison and upgrade decision engine."""
from typing import Dict, Any

class VersionComparator:
    def compare(self, baseline: Dict[str, Any], candidate: Dict[str, Any], lab_report: Dict[str, Any]) -> Dict[str, Any]:
        scores = {
            "performance": 0.0,
            "security": 0.0,
            "stability": 0.0,
            "maintainability": 0.0
        }
        
        b_dur = baseline.get("duration_sec", 1.0)
        c_dur = candidate.get("duration_sec", 1.0)

        # Performance comparison
        if b_dur > 0:
            perf_ratio = b_dur / max(c_dur, 0.001)
            scores["performance"] = min(100, perf_ratio * 50)
        else:
            scores["performance"] = 50.0

        # Security & Maintainability from lab
        scores["security"] = lab_report.get("scores", {}).get("security", 50)
        scores["maintainability"] = lab_report.get("scores", {}).get("maintainability", 50)

        # Stability (test success + no crashes)
        scores["stability"] = 100.0 if candidate.get("success") and lab_report.get("passed") else 0.0

        total_score = sum(scores.values()) / len(scores)
        baseline_threshold = 60.0

        # Strict decision logic: Never approve objectively worse candidates
        decision = "APPROVE"
        if not candidate.get("success") or not lab_report.get("passed"):
            decision = "REJECT"
        elif c_dur > b_dur * 1.5:
            # Significant performance degradation triggers automatic rejection
            decision = "REJECT"
        elif total_score < baseline_threshold:
            decision = "REJECT"

        return {
            "decision": decision,
            "candidate_score": round(total_score, 2),
            "baseline_threshold": baseline_threshold,
            "breakdown": scores,
            "safe_to_upgrade": decision == "APPROVE"
        }
