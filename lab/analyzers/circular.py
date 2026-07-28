"""Circular dependency detection via DFS."""
import ast
from typing import Dict, Any, Set, List

class CircularDependencyAnalyzer:
    name = "circular_dependencies"
    def analyze(self, code: str, filename: str, context: Dict[str, Any]) -> Dict[str, Any]:
        graph = context.get("import_graph", {})
        issues = []
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    issues.append(f"Circular dependency detected: {node} -> {neighbor}")
                    return True
            rec_stack.discard(node)
            return False

        for node in graph:
            if node not in visited:
                dfs(node)

        score = 100 if not issues else 0
        return {"passed": len(issues) == 0, "score": score, "issues": issues}
