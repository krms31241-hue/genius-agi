"""Memory leak detection (static heuristics + sandbox metrics)."""
import ast
import re
from typing import Dict, Any

class MemoryAnalyzer:
    name = "memory"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        # Static heuristics
        if re.search(r"while\s+True:", code) and not re.search(r"break|return|raise", code):
            issues.append("Potential infinite loop causing memory exhaustion")
        if re.search(r"global\s+\w+", code):
            issues.append("Global state accumulation risk")
        unclosed = len(re.findall(r"open\(", code)) - len(re.findall(r"\.close\(\)|with\s+open", code))
        if unclosed > 0:
            issues.append(f"{unclosed} potentially unclosed file handles")

        # Sandbox metrics if available
        sandbox = context.get("sandbox_result")
        if sandbox and sandbox.memory_mb > 200:
            issues.append(f"High memory usage in sandbox: {sandbox.memory_mb:.1f}MB")

        score = max(0, 100 - len(issues) * 20)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
