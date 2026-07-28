"""Style validation (PEP8 basics)."""
import re
from typing import Dict, Any

class StyleAnalyzer:
    name = "style"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        lines = code.splitlines()
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(f"Line {i} exceeds 120 chars")
            if re.match(r"^\s*def\s+[A-Z]", line):
                issues.append(f"Line {i}: Function name should be lowercase")
            if "\t" in line:
                issues.append(f"Line {i}: Tab indentation detected")
        score = max(0, 100 - len(issues) * 5)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
