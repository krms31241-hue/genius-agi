"""Maintainability problem detection via metrics."""
import re
from typing import Dict, Any, List
from .base import BaseDetector

class MaintainabilityDetector(BaseDetector):
    name = "maintainability"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            lines = meta["line_count"]
            if lines > 500:
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": f"File too large: {lines} lines", "category": self.name})
            long_funcs = len(re.findall(r"def\s+\w+\([^)]*\):\n(?:.*\n){50,}", meta["content"]))
            if long_funcs > 0:
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": f"{long_funcs} function(s) exceed 50 lines", "category": self.name})
        return findings
