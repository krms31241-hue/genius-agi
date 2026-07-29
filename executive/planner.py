"""Planner: Generates executable plans with branching logic."""
import hashlib
import logging
from typing import List, Dict, Any
from .executive_models import Goal, PlanNode

logger = logging.getLogger(__name__)

class Planner:
    """Converts decomposed goals into structured execution plans."""
    def create_plan(self, goals: List[Goal]) -> List[PlanNode]:
        nodes = []
        # Precompute atomic goal IDs to filter orphan dependencies
        atomic_ids = {g.id for g in goals if g.metadata.get("atomic", False)}
        
        for g in goals:
            if not g.metadata.get("atomic", False):
                continue
                
            nid = hashlib.sha256(f"plan_{g.id}".encode()).hexdigest()[:12]
            branch = "sequential"
            if g.metadata.get("risk", 0) > 0.6: branch = "conditional"
            if g.metadata.get("fallback", False): branch = "fallback"
            if g.metadata.get("recovery", False): branch = "recovery"
            if g.metadata.get("parallel", False): branch = "parallel"

            # Map dependencies to plan node IDs, filtering out non-atomic/missing parents
            plan_deps = [hashlib.sha256(f"plan_{d}".encode()).hexdigest()[:12] for d in g.dependencies if d in atomic_ids]

            nodes.append(PlanNode(
                id=nid, action=g.description, dependencies=plan_deps,
                expected_result=f"Completion of {g.title}", risk=g.metadata.get("risk", 0.3),
                estimated_cost=g.metadata.get("resource_cost", 1.0), branch_type=branch,
                metadata={"goal_id": g.id}
            ))
        logger.info("Generated plan with %d nodes", len(nodes))
        return nodes
