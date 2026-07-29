"""Simulation Scenario: Isolated world clone and action application tracker."""
import copy
import logging
from typing import Dict, Any
from executive.world.world_model import WorldModel
from .simulation_models import SimulationAction

logger = logging.getLogger(__name__)

class SimulationScenario:
    """Maintains a deep-copied world state for safe, non-destructive simulation."""
    def __init__(self, world_model: WorldModel) -> None:
        self.cloned_world: WorldModel = copy.deepcopy(world_model)
        self.changes: list[Dict[str, Any]] = []
        self.risks: list[Dict[str, Any]] = []

    def apply_action(self, action: SimulationAction) -> bool:
        """Apply a single action to the cloned world and record outcomes."""
        try:
            if action.action_type == "create":
                entity_type = action.parameters.get("entity_type", "simulated_entity")
                attrs = action.parameters.get("attributes", {})
                meta = action.parameters.get("metadata", {})
                rels = action.parameters.get("relationships", {})
                new_entity = self.cloned_world.create_entity(entity_type, attrs, rels, meta)
                self.changes.append({
                    "action_id": action.id, "type": "create",
                    "target": new_entity.id, "status": "applied"
                })
                return True

            elif action.action_type == "update":
                if not action.target_entity_id:
                    self.risks.append({"action_id": action.id, "reason": "Missing target_entity_id for update"})
                    return False
                existing = self.cloned_world.get_entity(action.target_entity_id)
                if not existing:
                    self.risks.append({"action_id": action.id, "reason": f"Entity {action.target_entity_id} not found for update"})
                    return False
                self.cloned_world.update_entity(action.target_entity_id, action.parameters)
                self.changes.append({
                    "action_id": action.id, "type": "update",
                    "target": action.target_entity_id, "status": "applied"
                })
                return True

            elif action.action_type == "delete":
                if not action.target_entity_id:
                    self.risks.append({"action_id": action.id, "reason": "Missing target_entity_id for delete"})
                    return False
                existing = self.cloned_world.get_entity(action.target_entity_id)
                if not existing:
                    self.risks.append({"action_id": action.id, "reason": f"Entity {action.target_entity_id} not found for delete"})
                    return False
                self.cloned_world.delete_entity(action.target_entity_id)
                self.changes.append({
                    "action_id": action.id, "type": "delete",
                    "target": action.target_entity_id, "status": "applied"
                })
                return True

            else:
                self.risks.append({"action_id": action.id, "reason": f"Unknown action_type: {action.action_type}"})
                return False
        except Exception as e:
            self.risks.append({"action_id": action.id, "reason": f"Execution error: {str(e)}"})
            return False
