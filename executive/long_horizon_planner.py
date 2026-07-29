"""Long Horizon Planner: Mission decomposition, campaign generation, dynamic prioritization, and execution planning."""
import hashlib
import time
import logging
from typing import Dict, Any, List
from .campaign import Campaign, CampaignStatus
from .objective import Objective, ObjectiveStatus
from .goal_tree import GoalTree, HierarchyNode, NodeType, NodeStatus

logger = logging.getLogger(__name__)

class LongHorizonPlanner:
    """Deterministic long-horizon planning engine with full hierarchy management."""
    def __init__(self):
        self.tree = GoalTree()
        self.campaigns: Dict[str, Campaign] = {}
        self.objectives: Dict[str, Objective] = {}

    def decompose_mission(self, mission_id: str, mission_title: str, mission_objectives: List[str]) -> Dict[str, Any]:
        mission_node = HierarchyNode(id=mission_id, node_type=NodeType.MISSION, title=mission_title, status=NodeStatus.ACTIVE, priority=100.0)
        self.tree.add_node(mission_node)

        campaign_ids = []
        for i, obj in enumerate(mission_objectives):
            cid = self._hash_id(f"{mission_id}_camp_{i}")
            campaign = Campaign(id=cid, title=f"Campaign: {obj}", description=f"Execute {obj}", parent_mission_id=mission_id)
            self.campaigns[cid] = campaign
            camp_node = HierarchyNode(id=cid, node_type=NodeType.CAMPAIGN, title=campaign.title, parent_id=mission_id, priority=80.0)
            self.tree.add_node(camp_node)
            campaign_ids.append(cid)

            obj_count = 2 + (int(hashlib.md5(obj.encode()).hexdigest(), 16) % 3)
            prev_obj_id = None
            for j in range(obj_count):
                oid = self._hash_id(f"{cid}_obj_{j}")
                objective = Objective(id=oid, title=f"Objective {j+1} for {obj}", parent_campaign_id=cid, dependencies=[prev_obj_id] if prev_obj_id else [])
                self.objectives[oid] = objective
                obj_node = HierarchyNode(id=oid, node_type=NodeType.OBJECTIVE, title=objective.title, parent_id=cid, dependencies=objective.dependencies, priority=60.0)
                self.tree.add_node(obj_node)
                campaign.objectives.append(oid)
                prev_obj_id = oid

                goal_count = 1 + (int(hashlib.md5(f"{oid}_goal".encode()).hexdigest(), 16) % 2)
                for k in range(goal_count):
                    gid = self._hash_id(f"{oid}_goal_{k}")
                    goal_node = HierarchyNode(id=gid, node_type=NodeType.GOAL, title=f"Goal {k+1} for {objective.title}", parent_id=oid, priority=40.0)
                    self.tree.add_node(goal_node)

                    task_count = 1 + (int(hashlib.md5(f"{gid}_task".encode()).hexdigest(), 16) % 2)
                    prev_task_id = None
                    for t in range(task_count):
                        tid = self._hash_id(f"{gid}_task_{t}")
                        task_node = HierarchyNode(id=tid, node_type=NodeType.TASK, title=f"Task {t+1} for {goal_node.title}", parent_id=gid, dependencies=[prev_task_id] if prev_task_id else [], priority=20.0)
                        self.tree.add_node(task_node)
                        prev_task_id = tid

                        aid = self._hash_id(f"{tid}_action")
                        action_node = HierarchyNode(id=aid, node_type=NodeType.ACTION, title=f"Execute {task_node.title}", parent_id=tid, priority=10.0)
                        self.tree.add_node(action_node)

        logger.info("Decomposed mission %s into %d campaigns, %d total nodes", mission_id, len(campaign_ids), len(self.tree.nodes))
        return {"mission_id": mission_id, "campaigns": campaign_ids, "tree_nodes": len(self.tree.nodes)}

    def update_priorities(self, context: Dict[str, Any] = None) -> None:
        self.tree.reprioritize(context)
        logger.info("Dynamic reprioritization complete")

    def mark_completed(self, node_id: str) -> List[str]:
        propagated = self.tree.propagate_completion(node_id)
        for nid in propagated:
            if nid in self.campaigns:
                self.campaigns[nid].status = CampaignStatus.COMPLETED
                self.campaigns[nid].updated_at = time.time()
            if nid in self.objectives:
                self.objectives[nid].status = ObjectiveStatus.COMPLETED
                self.objectives[nid].updated_at = time.time()
        logger.info("Completion propagated from %s: %d nodes updated", node_id, len(propagated))
        return propagated

    def get_execution_plan(self) -> List[str]:
        try:
            return self.tree.topological_sort()
        except ValueError as e:
            logger.error("Execution plan generation failed: %s", e)
            return []

    def get_hierarchy(self) -> List[Dict[str, Any]]:
        return self.tree.get_hierarchy()

    def merge_goals(self, goal_ids: List[str], new_goal_id: str, new_title: str) -> bool:
        return self.tree.merge_goals(goal_ids, new_goal_id, new_title)

    def _hash_id(self, seed: str) -> str:
        return hashlib.sha256(seed.encode()).hexdigest()[:12]
