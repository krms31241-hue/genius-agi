"""Dead code detection via reference analysis."""
import ast
from typing import Dict, Any, List
from .base import BaseDetector

class DeadCodeDetector(BaseDetector):
    name = "dead_code"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        defined = {}
        used = set()

        for fpath, meta in file_map.items():
            try:
                tree = ast.parse(meta["content"])
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined[node.name] = {"file": fpath, "line": node.lineno}
                elif isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used.add(node.attr)

        for name, info in defined.items():
            if name.startswith("_") or name in ("main", "setup", "teardown"):
                continue
            if name not in used:
                findings.append({
                    "file": info["file"],
                    "line": info["line"],
                    "severity": "low",
                    "reason": f"Potentially unused definition: {name}",
                    "category": self.name
                })
        return findings
