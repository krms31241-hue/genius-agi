from __future__ import annotations

import json
import os
from typing import Dict, Any

DEFAULT = {
    "accepted": False,
    "mode": "balanced",
    "custom": {
        "cpu": 35.0,
        "memory": 30.0,
        "disk": 20.0,
    },
}


class UserConsentManager:
    def __init__(self, data_dir="executive_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "user_consent.json")
        self._ensure()

    def _ensure(self):
        if not os.path.exists(self.path):
            self.save(DEFAULT)

    def load(self) -> Dict[str, Any]:
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def accepted(self) -> bool:
        return self.load()["accepted"]

    def accept(self, mode="balanced"):
        data = self.load()
        data["accepted"] = True
        data["mode"] = mode
        self.save(data)

    def revoke(self):
        data = self.load()
        data["accepted"] = False
        self.save(data)

    def mode(self):
        return self.load()["mode"]

    def custom_limits(self):
        return self.load()["custom"]

    def set_custom_limits(self, cpu, memory, disk):
        data = self.load()
        data["mode"] = "custom"
        data["custom"] = {
            "cpu": float(cpu),
            "memory": float(memory),
            "disk": float(disk),
        }
        self.save(data)
