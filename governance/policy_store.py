"""Persistent storage for policies, axioms, and history with atomic operations."""
import os
import json
import time
import shutil
import tempfile
import logging
from typing import Dict, Any, List, Optional
from .policy import Policy
from .core_axioms import CoreAxiom

logger = logging.getLogger(__name__)

class PolicyStore:
    def __init__(self, data_dir: str = "governance_data"):
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.policies_path = os.path.join(self.data_dir, "policies.json")
        self.axioms_path = os.path.join(self.data_dir, "axioms.json")
        self.history_path = os.path.join(self.data_dir, "history.json")
        self._init_files()

    def _init_files(self):
        for p in [self.policies_path, self.axioms_path, self.history_path]:
            if not os.path.exists(p):
                self._atomic_save(p, [])

    def _atomic_save(self, path: str, data: Any):
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise

    def _load_json(self, path: str) -> List[Dict[str, Any]]:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def add(self, policy: Policy) -> bool:
        data = self._load_json(self.policies_path)
        data.append(policy.to_dict())
        self._atomic_save(self.policies_path, data)
        self._record_history("add", policy)
        logger.info("Policy added: %s v%s", policy.id, policy.version)
        return True

    def update(self, policy: Policy) -> bool:
        data = self._load_json(self.policies_path)
        for i, p in enumerate(data):
            if p["id"] == policy.id:
                new_dict = policy.to_dict()
                # Prevent stale policy objects from accidentally downgrading status during partial updates
                if new_dict.get("status") == "draft" and p.get("status") not in ("draft", None):
                    new_dict["status"] = p["status"]
                new_dict["updated_at"] = time.time()
                data[i] = new_dict
                self._atomic_save(self.policies_path, data)
                self._record_history("update", policy)
                logger.info("Policy updated: %s v%s", policy.id, policy.version)
                return True
        return False

    def remove(self, policy_id: str) -> bool:
        data = self._load_json(self.policies_path)
        new_data = [p for p in data if p["id"] != policy_id]
        if len(new_data) == len(data):
            return False
        self._atomic_save(self.policies_path, new_data)
        self._record_history("remove", Policy(id=policy_id))
        logger.info("Policy removed: %s", policy_id)
        return True

    def latest(self, policy_id: str) -> Optional[Policy]:
        data = self._load_json(self.policies_path)
        for p in reversed(data):
            if p["id"] == policy_id:
                return Policy.from_dict(p)
        return None

    def history(self, policy_id: str = None) -> List[Dict[str, Any]]:
        hist = self._load_json(self.history_path)
        if policy_id:
            return [h for h in hist if h.get("policy_id") == policy_id]
        return hist

    def rollback(self, policy_id: str, target_version: str) -> bool:
        hist = self.history(policy_id)
        target_snapshot = None
        for h in reversed(hist):
            if h.get("version") == target_version and h.get("action") in ("add", "update"):
                target_snapshot = h.get("snapshot")
                break
        if not target_snapshot:
            logger.warning("Rollback target not found: %s v%s", policy_id, target_version)
            return False
        
        restored = Policy.from_dict(target_snapshot)
        restored.updated_at = time.time()
        success = self.update(restored)
        if success:
            self._record_history("rollback", restored)
            logger.info("Policy rolled back: %s to v%s", policy_id, target_version)
        return success

    def load_policies(self) -> List[Policy]:
        data = self._load_json(self.policies_path)
        return [Policy.from_dict(p) for p in data]

    def load_axioms(self) -> List[CoreAxiom]:
        data = self._load_json(self.axioms_path)
        return [CoreAxiom.from_dict(a) for a in data]

    def save_axioms(self, axioms: List[CoreAxiom]) -> bool:
        self._atomic_save(self.axioms_path, [a.to_dict() for a in axioms])
        logger.info("Axioms saved: %d", len(axioms))
        return True

    def _record_history(self, action: str, policy: Policy):
        hist = self._load_json(self.history_path)
        hist.append({
            "action": action,
            "policy_id": policy.id,
            "version": policy.version,
            "snapshot": policy.to_dict(),
            "timestamp": time.time()
        })
        self._atomic_save(self.history_path, hist)
