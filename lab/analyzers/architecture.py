"""Architecture validation (layering & coupling)."""
import re
from typing import Dict, Any

class ArchitectureAnalyzer:
    name = "architecture"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        # Simple layer violation detection
        if "ui" in filename.lower() and re.search(r"import\s+(db|database|models)", code):
            issues.append("UI layer importing database directly")
        if "controller" in filename.lower() and re.search(r"import\s+ui", code):
            issues.append("Controller importing UI layer")
        coupling = len(set(re.findall(r"import\s+([\w\.]+)", code)))
        if coupling > 10:
            issues.append(f"High module coupling: {coupling} imports")
        score = max(0, 100 - len(issues) * 20)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
