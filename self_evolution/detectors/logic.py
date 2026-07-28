"""Logical problem detection via control flow heuristics."""
import ast
import re
from typing import Dict, Any, List
from .base import BaseDetector

class LogicDetector(BaseDetector):
    name = "logic"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            code = meta["content"]
            if re.search(r"if\s+\w+\s*==\s*True:|if\s+\w+\s*==\s*False:", code):
                findings.append({"file": fpath, "line": 1, "severity": "low", "reason": "Redundant boolean comparison", "category": self.name})
            if re.search(r"except\s+Exception\s+as\s+e:\s*\n\s*pass", code):
                findings.append({"file": fpath, "line": 1, "severity": "high", "reason": "Silently swallowed exception", "category": self.name})
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, ast.If):
                        if isinstance(node.test, ast.Constant) and node.test.value in (True, False):
                            findings.append({"file": fpath, "line": node.lineno, "severity": "low", "reason": "Constant condition in if statement", "category": self.name})
            except SyntaxError:
                pass
        return findings
