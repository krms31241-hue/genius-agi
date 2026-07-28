"""Syntax validation via AST."""
import ast
from typing import Dict, Any

class SyntaxAnalyzer:
    name = "syntax"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            ast.parse(code, filename=filename)
            return {"passed": True, "score": 100, "issues": []}
        except SyntaxError as e:
            return {"passed": False, "score": 0, "issues": [f"SyntaxError: {e.msg} at line {e.lineno}"]}
