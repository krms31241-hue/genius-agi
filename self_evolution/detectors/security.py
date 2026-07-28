"""Security problem detection via AST & pattern matching."""
import ast
import re
from typing import Dict, Any, List
from .base import BaseDetector

DANGEROUS = {"eval", "exec", "compile", "__import__", "pickle.loads", "os.system", "os.popen", "subprocess.call"}

class SecurityDetector(BaseDetector):
    name = "security"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        for fpath, meta in file_map.items():
            try:
                tree = ast.parse(meta["content"])
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    fname = self._get_name(node.func)
                    if fname in DANGEROUS:
                        findings.append({"file": fpath, "line": node.lineno, "severity": "high", "reason": f"Unsafe call: {fname}", "category": self.name})
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if re.search(r"(password|secret|api_key|token)\s*=\s*['\"].+['\"]", node.value, re.I):
                        findings.append({"file": fpath, "line": node.lineno, "severity": "high", "reason": "Hardcoded secret detected", "category": self.name})
        return findings

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name): return node.id
        if isinstance(node, ast.Attribute): return f"{self._get_name(node.value)}.{node.attr}"
        return ""
