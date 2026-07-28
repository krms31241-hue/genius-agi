"""Project inspection and internal file mapping."""
import os
import hashlib
from typing import Dict, Any, List
from .config import PROJECT_ROOT, IGNORE_DIRS, SUPPORTED_EXTENSIONS

class ProjectMapper:
    def inspect(self, root_dir: str = PROJECT_ROOT) -> Dict[str, Dict[str, Any]]:
        file_map = {}
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
            for fname in filenames:
                ext = os.path.splitext(fname)[1]
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                fpath = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(fpath, root_dir)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    file_map[rel_path] = {
                        "abs_path": fpath,
                        "content": content,
                        "lines": content.splitlines(),
                        "line_count": len(content.splitlines()),
                        "size_bytes": os.path.getsize(fpath),
                        "hash": hashlib.sha256(content.encode("utf-8")).hexdigest()[:16],
                        "extension": ext
                    }
                except Exception:
                    continue
        return file_map
