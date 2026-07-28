"""Security scanning via AST pattern matching."""
import ast
from typing import Dict, Any

DANGEROUS_CALLS = {"eval", "exec", "compile", "__import__", "pickle.loads", "subprocess.call", "subprocess.run", "os.system", "os.popen"}
DANGEROUS_ATTRS = {"shell", "globals", "locals"}

class SecurityAnalyzer:
    name = "security"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"passed": False, "score": 0, "issues": ["AST parse failed"]}

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_name(node.func)
                if func_name in DANGEROUS_CALLS:
                    issues.append(f"Unsafe call: {func_name}")
                if isinstance(node, ast.Call) and hasattr(node, "keywords"):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            issues.append("shell=True detected in subprocess")
            elif isinstance(node, ast.Attribute):
                if node.attr in DANGEROUS_ATTRS:
                    issues.append(f"Sensitive attribute access: {node.attr}")

        score = max(0, 100 - len(issues) * 25)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}

    def _get_name(self, node) -> str:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""
