"""Duplicated code detection via block hashing."""
import hashlib
from typing import Dict, Any, List
from .base import BaseDetector

class DuplicationDetector(BaseDetector):
    name = "duplication"

    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        findings = []
        block_hashes = {}
        for fpath, meta in file_map.items():
            lines = meta["lines"]
            for i in range(0, len(lines) - 4, 3):
                block = "\n".join(lines[i:i+5]).strip()
                if len(block) < 50:
                    continue
                h = hashlib.md5(block.encode()).hexdigest()
                if h in block_hashes:
                    findings.append({
                        "file": fpath,
                        "line": i + 1,
                        "severity": "medium",
                        "reason": f"Duplicated block also in {block_hashes[h]}",
                        "category": self.name
                    })
                else:
                    block_hashes[h] = fpath
        return findings
