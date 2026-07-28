"""Dependency validation against requirements."""
import re
from typing import Dict, Any

class DependencyAnalyzer:
    name = "dependencies"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        reqs = context.get("requirements", [])
        issues = []
        imported = set(re.findall(r"^\s*(?:import|from)\s+([\w\.]+)", code, re.MULTILINE))
        for imp in imported:
            base = imp.split(".")[0]
            if base not in reqs and base not in ("os", "sys", "json", "ast", "re", "time", "typing", "pathlib", "subprocess", "tempfile", "shutil", "hashlib", "sqlite3", "threading", "signal", "resource"):
                issues.append(f"Undeclared dependency: {base}")
        score = max(0, 100 - len(issues) * 15)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
