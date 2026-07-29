"""Replanner: Regenerates unfinished branches while preserving completed work."""
import logging
from typing import List, Dict, Any
from .executive_models import PlanNode, GoalStatus, TaskState
from .task_graph import TaskGraph

logger = logging.getLogger(__name__)

class Replanner:
    def replan(self, graph: TaskGraph, states: Dict[str, TaskState], failed_nodes: List[str]) -> TaskGraph:
        new_graph = TaskGraph()
        completed = {tid for tid, st in states.items() if st.status == GoalStatus.COMPLETED}
        valid_nodes = {nid for nid in graph.nodes if nid in completed or nid not in failed_nodes}
        
        for nid in valid_nodes:
            node = graph.nodes[nid]
            new_deps = [d for d in node.dependencies if d in valid_nodes]
            new_node = PlanNode(id=node.id, action=node.action, dependencies=new_deps,
                                expected_result=node.expected_result, risk=node.risk,
                                estimated_cost=node.estimated_cost, branch_type=node.branch_type,
                                metadata=node.metadata.copy())
            new_graph.add_node(new_node)
            
        for fid in failed_nodes:
            alt_id = f"{fid}_alt"
            alt_node = PlanNode(id=alt_id, action=f"Alternative path for {graph.nodes[fid].action}",
                                dependencies=[d for d in graph.nodes[fid].dependencies if d in valid_nodes],
                                expected_result="Recovery completion", risk=0.4, estimated_cost=1.5,
                                branch_type="recovery", metadata={"replaces": fid})
            new_graph.add_node(alt_node)
            
        logger.info("Replanning complete: kept %d valid, regenerated %d alternatives", len(valid_nodes), len(failed_nodes))
        return new_graph
