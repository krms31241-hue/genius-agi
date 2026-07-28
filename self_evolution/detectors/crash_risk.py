"""Possible crash detection via unsafe patterns."""
import ast
import re
from typing import Dict, Any, List
from .base import BaseDetector

class CrashRiskDetector(BaseDetector):
    name = "crash_risk"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            code = meta["content"]
            if re.search(r"except\s*:", code):
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": "Bare except hides crashes", "category": self.name})
            if re.search(r"\.pop\(\)|\.remove\(", code) and not re.search(r"if\s+\w+\s+in\s+\w+|try:", code):
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": "Unsafe collection mutation without guard", "category": self.name})
            if re.search(r"while\s+True:", code) and not re.search(r"break|return|raise|sys\.exit", code):
                findings.append({"file": fpath, "line": 1, "severity": "high", "reason": "Infinite loop without exit condition", "category": self.name})
        return findings
