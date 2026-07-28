"""Performance estimation via complexity + timing."""
import ast
from typing import Dict, Any

class PerformanceAnalyzer:
    name = "performance"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        issues = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return {"passed": False, "score": 0, "issues": ["AST parse failed"]}

        depth = self._max_loop_depth(tree)
        if depth >= 4:
            issues.append(f"Deep nesting detected (depth {depth})")
        calls = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.Call))
        if calls > 50:
            issues.append(f"High call density: {calls} calls")

        sandbox = context.get("sandbox_result")
        if sandbox and sandbox.duration > 5.0:
            issues.append(f"Slow execution: {sandbox.duration:.2f}s")

        score = max(0, 100 - len(issues) * 25)
        return {"passed": len(issues) == 0, "score": score, "issues": issues}

    def _max_loop_depth(self, node, depth=0):
        if isinstance(node, (ast.For, ast.While)):
            depth += 1
        return max([depth] + [self._max_loop_depth(child, depth) for child in ast.iter_child_nodes(node)])
