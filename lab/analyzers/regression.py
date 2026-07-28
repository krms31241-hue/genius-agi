"""Regression detection via signature comparison."""
import hashlib
import re
from typing import Dict, Any

class RegressionAnalyzer:
    name = "regression"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        baseline = context.get("baseline_signatures", {})
        current_funcs = set(re.findall(r"def\s+(\w+)\s*\(", code))
        for func in baseline.get(filename, []):
            if func not in current_funcs:
                issues.append(f"Missing function: {func} (possible regression)")
        score = 100 if not issues else max(0, 100 - len(issues) * 30)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
