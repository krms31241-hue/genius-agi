"""Simulation Engine: Orchestrates safe cloning, action execution, and result generation."""
import logging
from typing import Union, List, Dict, Any
from executive.world.world_model import WorldModel
from .simulation_models import SimulationAction, SimulationPlan
from .simulation_result import SimulationResult
from .scenario import SimulationScenario

logger = logging.getLogger(__name__)

class SimulationEngine:
    """Production-grade simulator that never mutates the real WorldModel.
    Supports single actions, action lists, and structured plans."""
    
    def simulate(self, target: Union[SimulationAction, List[SimulationAction], SimulationPlan],
                 world_model: WorldModel) -> SimulationResult:
        """Execute simulation on an isolated clone and return predictions."""
        actions: List[SimulationAction] = []
        if isinstance(target, SimulationAction):
            actions = [target]
        elif isinstance(target, SimulationPlan):
            actions = target.actions
        elif isinstance(target, list):
            actions = target
        else:
            raise ValueError("Unsupported target type for simulation")

        scenario = SimulationScenario(world_model)
        success = True
        total_cost = 0.0
        total_duration = 0.0

        for action in actions:
            total_cost += action.estimated_cost
            total_duration += action.estimated_duration
            if not scenario.apply_action(action):
                success = False

        # Confidence degrades with accumulated risks
        confidence = max(0.1, 1.0 - (len(scenario.risks) * 0.15))
        
        # Rollback is possible if we successfully tracked changes or maintained a clean clone state
        rollback_possible = len(scenario.changes) > 0 or success

        logger.info("Simulation complete: success=%s, changes=%d, risks=%d, confidence=%.2f",
                    success, len(scenario.changes), len(scenario.risks), confidence)

        return SimulationResult(
            success=success,
            predicted_changes=scenario.changes,
            predicted_risks=scenario.risks,
            confidence=round(confidence, 3),
            estimated_cost=round(total_cost, 3),
            estimated_duration=round(total_duration, 3),
            rollback_possible=rollback_possible
        )
