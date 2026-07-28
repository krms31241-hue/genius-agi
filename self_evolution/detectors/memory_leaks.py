"""Memory leak detection via static heuristics."""
import re
from typing import Dict, Any, List
from .base import BaseDetector

class MemoryLeakDetector(BaseDetector):
    name = "memory_leaks"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            code = meta["content"]
            opens = len(re.findall(r"\bopen\(", code))
            closes = len(re.findall(r"\.close\(\)", code)) + len(re.findall(r"with\s+open", code))
            if opens > closes:
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": f"{opens - closes} potentially unclosed file handle(s)", "category": self.name})
            if re.search(r"global\s+\w+", code) and re.search(r"\[\]\s*=\s*\[\]|\{\}\s*=\s*\{\}", code):
                findings.append({"file": fpath, "line": 1, "severity": "low", "reason": "Global mutable state accumulation risk", "category": self.name})
        return findings
