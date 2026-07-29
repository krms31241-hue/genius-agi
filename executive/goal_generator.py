"""Autonomous Goal Generator."""
import time
import hashlib
import logging
from typing import Dict, Any, List
from .executive_models import Goal, GoalStatus

logger = logging.getLogger(__name__)

class GoalGenerator:
    """Generates autonomous goals from system telemetry, memory, decisions, governance, and failures."""
    def generate(self, context: Dict[str, Any]) -> List[Goal]:
        goals = []
        mem = context.get("memory_stats", {})
        dec = context.get("decision_stats", {})
        gov = context.get("governance_stats", {})
        fail = context.get("failure_stats", {})
        user = context.get("user_requests", [])

        if mem.get("recall_rate", 100) < 75:
            goals.append(self._create_goal("memory_optimization", "Improve semantic recall rate", importance=0.8, urgency=0.7, origin="memory_telemetry"))
        if dec.get("avg_confidence", 1.0) < 0.65:
            goals.append(self._create_goal("decision_calibration", "Increase decision consensus threshold", importance=0.9, urgency=0.8, origin="decision_engine"))
        if gov.get("policy_violations", 0) > 0:
            goals.append(self._create_goal("governance_compliance", "Resolve active policy violations", importance=1.0, urgency=0.9, origin="governance_engine"))
        if fail.get("recent_failures", 0) > 3:
            goals.append(self._create_goal("failure_mitigation", "Address recurring execution failures", importance=0.9, urgency=0.85, origin="failure_history"))
        if mem.get("compression_ratio", 0) > 0.4:
            goals.append(self._create_goal("memory_defragmentation", "Compress and deduplicate memory store", importance=0.6, urgency=0.4, origin="memory_telemetry"))
        for req in user:
            goals.append(self._create_goal(f"user_{req.get('id', 'req')}", req.get("description", "User request"), importance=req.get("importance", 0.7), urgency=req.get("urgency", 0.6), origin="user"))

        if not goals:
            goals.append(self._create_goal("system_maintenance", "Routine capability enhancement", importance=0.5, urgency=0.3, origin="system"))

        logger.info("Generated %d autonomous goals", len(goals))
        return goals

    def _create_goal(self, title: str, desc: str, importance: float, urgency: float, origin: str) -> Goal:
        gid = hashlib.sha256(f"{title}_{time.time()}".encode()).hexdigest()[:12]
        return Goal(id=gid, title=title, description=desc, importance=importance, urgency=urgency, origin=origin, status=GoalStatus.NEW)
