"""Import validation."""
import ast
import importlib.util
import sys
from typing import Dict, Any

class ImportAnalyzer:
    name = "imports"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"passed": False, "score": 0, "issues": ["Cannot parse AST for import check"]}

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if not self._module_exists(alias.name):
                        issues.append(f"Missing module: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and not self._module_exists(node.module):
                    issues.append(f"Missing module: {node.module}")

        score = max(0, 100 - len(issues) * 20)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}

    def _module_exists(self, name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except Exception:
            return False
