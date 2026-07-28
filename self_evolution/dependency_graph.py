"""Dependency graph builder and cycle detector."""
import re
import ast
from typing import Dict, Any, List, Set, Tuple

class DependencyGraph:
    def build(self, file_map: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        graph = {f: {"imports": set(), "imported_by": set()} for f in file_map}
        module_map = {}

        for fpath, meta in file_map.items():
            mod_name = fpath.replace("/", ".").replace("\\", ".").removesuffix(".py")
            module_map[mod_name] = fpath

        for fpath, meta in file_map.items():
            try:
                tree = ast.parse(meta["content"], filename=fpath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self._link(graph, fpath, alias.name, module_map)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        self._link(graph, fpath, node.module, module_map)

        cycles = self._detect_cycles(graph)
        return {"graph": graph, "cycles": cycles, "module_map": module_map}

    def _link(self, graph: Dict, source: str, target_mod: str, module_map: Dict[str, str]):
        base = target_mod.split(".")[0]
        target_file = module_map.get(target_mod) or module_map.get(base)
        if target_file and target_file in graph:
            graph[source]["imports"].add(target_file)
            graph[target_file]["imported_by"].add(source)

    def _detect_cycles(self, graph: Dict) -> List[List[str]]:
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, {}).get("imports", set()):
                if neighbor not in visited:
                    dfs(neighbor)
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    cycles.append(path[cycle_start:] + [neighbor])
            path.pop()
            rec_stack.discard(node)

        for node in graph:
            if node not in visited:
                dfs(node)
        return cycles
