"""Performance issue detection via complexity & patterns."""
import ast
import re
from typing import Dict, Any, List
from .base import BaseDetector

class PerformanceDetector(BaseDetector):
    name = "performance"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            try:
                tree = ast.parse(meta["content"])
            except SyntaxError:
                continue
            depth = self._max_loop_depth(tree)
            if depth >= 4:
                findings.append({"file": fpath, "line": 1, "severity": "high", "reason": f"Deep nesting depth: {depth}", "category": self.name})
            if re.search(r"\.append\(", meta["content"]) and re.search(r"for\s+\w+\s+in\s+range\(", meta["content"]):
                findings.append({"file": fpath, "line": 1, "severity": "medium", "reason": "List growth in loop may cause reallocation overhead", "category": self.name})
        return findings

    def _max_loop_depth(self, node, depth=0):
        if isinstance(node, (ast.For, ast.While)):
            depth += 1
        return max([depth] + [self._max_loop_depth(c, depth) for c in ast.iter_child_nodes(node)])
