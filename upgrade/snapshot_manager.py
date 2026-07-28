"""Atomic snapshot, archive, activation, and rollback."""
import os
import shutil
import json
import time
import hashlib
from typing import Dict, List, Optional

class SnapshotManager:
    def __init__(self, versions_dir: str = ".project_versions"):
        self.versions_dir = versions_dir
        os.makedirs(versions_dir, exist_ok=True)
        self.manifest_path = os.path.join(versions_dir, "manifest.json")
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> Dict:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"active": None, "history": []}

    def _save_manifest(self):
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)

    def _hash_dir(self, path: str) -> str:
        h = hashlib.sha256()
        for root, _, files in os.walk(path):
            for fn in sorted(files):
                fp = os.path.join(root, fn)
                if ".project_versions" in fp or ".upgrade_state" in fp:
                    continue
                with open(fp, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
        return h.hexdigest()[:16]

    def create_snapshot(self, project_dir: str) -> str:
        snap_id = f"v_{int(time.time())}_{self._hash_dir(project_dir)}"
        snap_path = os.path.join(self.versions_dir, snap_id)
        shutil.copytree(project_dir, snap_path, ignore=shutil.ignore_patterns(self.versions_dir, ".git", "__pycache__", "*.pyc", ".upgrade_state.json"))
        self.manifest["history"].append({"id": snap_id, "timestamp": time.time(), "type": "snapshot"})
        self._save_manifest()
        return snap_id

    def archive_current(self, project_dir: str) -> str:
        arch_id = f"arch_{int(time.time())}"
        arch_path = os.path.join(self.versions_dir, arch_id)
        shutil.copytree(project_dir, arch_path, ignore=shutil.ignore_patterns(self.versions_dir, ".git", "__pycache__", "*.pyc", ".upgrade_state.json"))
        self.manifest["history"].append({"id": arch_id, "timestamp": time.time(), "type": "archive"})
        self._save_manifest()
        return arch_id

    def activate(self, snap_id: str, project_dir: str) -> bool:
        snap_path = os.path.join(self.versions_dir, snap_id)
        if not os.path.exists(snap_path):
            return False
        # Atomic swap via temp dir
        temp_dir = project_dir + ".tmp_upgrade"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        shutil.copytree(snap_path, temp_dir)
        # Replace contents
        for item in os.listdir(project_dir):
            if item in (".project_versions", ".git", ".upgrade_state.json"):
                continue
            target = os.path.join(project_dir, item)
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
        for item in os.listdir(temp_dir):
            shutil.move(os.path.join(temp_dir, item), os.path.join(project_dir, item))
        shutil.rmtree(temp_dir)
        self.manifest["active"] = snap_id
        self._save_manifest()
        return True

    def rollback(self, target_id: str, project_dir: str) -> bool:
        return self.activate(target_id, project_dir)
