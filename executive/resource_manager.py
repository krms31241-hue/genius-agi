import os
import json
import logging
from executive.user_consent import UserConsentManager
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class ResourceManager:
    """
    Manages resource allocation and tracks usage.
    Phase 2 Upgrade: Integrates real hardware metrics via SystemResourceDetector
    while maintaining 100% backward compatibility with existing scheduler logic.
    """

    def __init__(self, data_dir: str = "executive_data", budgets: Dict[str, float] = None):
        self.data_dir = data_dir
        self.state_path = os.path.join(self.data_dir, "resources.json")
        self.budgets = budgets or {
            "cpu": 90.0,
            "memory": 90.0,
            "disk": 90.0,
            "max_concurrent": 10,
            "execution": 1000.0,
            "time": 3600.0
        }
        self.allocated = {}
        
        # Initialize hardware detector without altering constructor signature
        self.detector = None
        try:
            from executive.system_resource_detector import SystemResourceDetector
            self.detector = SystemResourceDetector()
        except Exception as e:
            logger.warning(f"Failed to initialize SystemResourceDetector: {e}. Falling back to legacy behavior.")
            
        # Load persisted state
        self._load_state()
        self.user_consent = UserConsentManager()

    def _load_state(self):
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    state = json.load(f)
                    self.allocated = state.get("allocated", {})
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.state_path, 'w') as f:
                json.dump({"allocated": self.allocated}, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def allocate(self, task_id: str, resources: Dict[str, Any] = None) -> bool:
        resources = resources or {}

        max_conc = self.budgets.get("max_concurrent", float("inf"))
        if len(self.allocated) >= max_conc:
            logger.warning("Max concurrent tasks reached. Cannot allocate %s", task_id)
            return False

        self.allocated[task_id] = resources
        self._save_state()
        return True

    def release(self, task_id: str) -> bool:
        """Releases resources for a given task."""
        if task_id in self.allocated:
            del self.allocated[task_id]
            self._save_state()
        return True

    def _get_legacy_usage(self) -> Dict[str, Any]:
        usage = {
            "cpu": 0.0,
            "memory": 0.0,
            "disk": 0.0,
            "execution": 0.0,
            "time": 0.0,
            "concurrent": len(self.allocated),
        }

        for cost in self.allocated.values():
            for k in usage:
                if k in cost:
                    usage[k] += cost[k]

        return usage

    def get_usage(self) -> Dict[str, Any]:
        return self._get_legacy_usage()

    def get_system_resources(self) -> Dict[str, Any]:
        if self.detector:
            try:
                return self.detector.detect()
            except Exception as e:
                logger.error("Detector failed: %s", e)
        return {}

    def predict_exhaustion(self) -> Dict[str, bool]:
        usage = self.get_usage()
        return {
            k: usage.get(k, 0) >= self.budgets.get(k, float("inf")) * 0.9
            for k in self.budgets
            if k != "max_concurrent"
        }

    def recommend_adjustments(self) -> List[str]:
        recommendations = []
        usage = self.get_usage()

        if usage.get("concurrent", 0) >= self.budgets.get("max_concurrent", float("inf")):
            recommendations.append(
                "Reduce concurrency: defer low-priority tasks"
            )

        if usage.get("memory", 0) >= self.budgets.get("memory", float("inf")) * 0.8:
            recommendations.append(
                "Memory pressure high: schedule garbage collection or swap tasks"
            )

        if usage.get("time", 0) >= self.budgets.get("time", float("inf")) * 0.8:
            recommendations.append(
                "Time budget nearing limit: prioritize critical path tasks"
            )

        return recommendations

    def get_resource_policy(self, mode="balanced"):
        from executive.resource_policy import ResourcePolicy, ResourceMode

        mode = mode.lower()

        mapping = {
            "eco": ResourceMode.ECO,
            "balanced": ResourceMode.BALANCED,
            "performance": ResourceMode.PERFORMANCE,
        }

        return ResourcePolicy(mapping.get(mode, ResourceMode.BALANCED))

    def evaluate_resources(self, mode=None):
        """
        Returns a real-time scheduling decision.
        """
        if mode is None:
            mode = self.get_current_mode()
        policy = self.get_resource_policy(mode)
        system = self.get_system_resources()
        return policy.evaluate(system)

    def can_schedule(self, mode="balanced"):
        return self.evaluate_resources(mode)["allow_new_tasks"]

    def requires_user_permission(self, mode="balanced"):
        policy = self.get_resource_policy(mode)
        system = self.get_system_resources()
        return policy.should_request_user_permission(system)



    def get_current_mode(self):
        return self.user_consent.mode()



    def get_effective_limits(self):
        """
        Returns actual resource limits based on user consent mode.
        """
        mode = self.get_current_mode()

        limits = {
            "eco": {
                "cpu": 30,
                "memory": 30,
                "disk": 20,
            },
            "balanced": {
                "cpu": 60,
                "memory": 60,
                "disk": 50,
            },
            "performance": {
                "cpu": 90,
                "memory": 90,
                "disk": 90,
            },
        }

        return limits.get(mode, limits["balanced"])
