"""Architecture problem detection via layering & coupling."""
from typing import Dict, Any, List
from .base import BaseDetector

class ArchitectureDetector(BaseDetector):
    name = "architecture"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        graph = dep_graph.get("graph", {})
        cycles = dep_graph.get("cycles", [])
        for cycle in cycles:
            findings.append({"file": cycle[0], "line": 1, "severity": "high", "reason": f"Circular dependency: {' -> '.join(cycle)}", "category": self.name})
        for fpath, meta in graph.items():
            coupling = len(meta.get("imports", set()))
            if coupling > 12:
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": f"High coupling: {coupling} imports", "category": self.name})
        return findings
