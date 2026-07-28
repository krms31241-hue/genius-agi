"""Rollback mechanism for failed patches."""
import os
import shutil
import json
import time
from typing import Dict, Any

class RollbackManager:
    def __init__(self, backup_dir: str = ".lab_backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)

    def snapshot(self, files: Dict[str, str]) -> str:
        snap_id = f"snap_{int(time.time())}"
        snap_path = os.path.join(self.backup_dir, snap_id)
        os.makedirs(snap_path, exist_ok=True)
        for fname, content in files.items():
            fpath = os.path.join(snap_path, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
        meta = {"id": snap_id, "files": list(files.keys()), "timestamp": time.time()}
        with open(os.path.join(snap_path, "meta.json"), "w") as f:
            json.dump(meta, f)
        return snap_id

    def restore(self, snap_id: str, target_dir: str = ".") -> bool:
        snap_path = os.path.join(self.backup_dir, snap_id)
        if not os.path.exists(snap_path):
            return False
        meta_path = os.path.join(snap_path, "meta.json")
        if not os.path.exists(meta_path):
            return False
        with open(meta_path) as f:
            meta = json.load(f)
        for fname in meta["files"]:
            src = os.path.join(snap_path, fname)
            dst = os.path.join(target_dir, fname)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
        return True

    def cleanup_old(self, max_age_sec: int = 86400):
        now = time.time()
        for d in os.listdir(self.backup_dir):
            meta = os.path.join(self.backup_dir, d, "meta.json")
            if os.path.exists(meta):
                with open(meta) as f:
                    ts = json.load(f).get("timestamp", 0)
                if now - ts > max_age_sec:
                    shutil.rmtree(os.path.join(self.backup_dir, d), ignore_errors=True)
