"""Project inspection and metric collection."""
import os
import ast
import re
from typing import Dict, Any, List

class ProjectInspector:
    def inspect(self, project_dir: str) -> Dict[str, Any]:
        metrics = {
            "files": [],
            "total_lines": 0,
            "complexity_score": 0,
            "dependencies": set(),
            "functions": [],
            "classes": []
        }
        for root, _, files in os.walk(project_dir):
            if any(skip in root for skip in (".git", "__pycache__", ".project_versions", "venv", "env")):
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                fpath = os.path.join(root, fn)
                rel = os.path.relpath(fpath, project_dir)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        code = f.read()
                    lines = code.splitlines()
                    metrics["total_lines"] += len(lines)
                    metrics["files"].append(rel)
                    metrics["complexity_score"] += self._estimate_complexity(code)
                    metrics["dependencies"].update(re.findall(r"^\s*(?:import|from)\s+([\w\.]+)", code, re.MULTILINE))
                    tree = ast.parse(code)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            metrics["functions"].append(f"{rel}:{node.name}")
                        elif isinstance(node, ast.ClassDef):
                            metrics["classes"].append(f"{rel}:{node.name}")
                except Exception:
                    continue
        metrics["dependencies"] = list(metrics["dependencies"])
        return metrics

    def _estimate_complexity(self, code: str) -> int:
        score = 0
        score += code.count("if ") + code.count("elif ")
        score += code.count("for ") + code.count("while ")
        score += code.count("try:") + code.count("except ")
        score += code.count(" and ") + code.count(" or ")
        return score
