"""Syntax problem detection via AST parsing."""
import ast
from typing import Dict, Any, List
from .base import BaseDetector

class SyntaxDetector(BaseDetector):
    name = "syntax"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            try:
                ast.parse(meta["content"], filename=fpath)
            except SyntaxError as e:
                findings.append({
                    "file": fpath,
                    "line": e.lineno or 1,
                    "severity": "high",
                    "reason": f"SyntaxError: {e.msg}",
                    "category": self.name
                })
        return findings
