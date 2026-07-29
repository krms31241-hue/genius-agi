"""Goal Decomposer: Recursive splitting into sub-goals and tasks."""
import hashlib
import time
import logging
from typing import List, Dict, Any
from .executive_models import Goal, GoalStatus

logger = logging.getLogger(__name__)

class GoalDecomposer:
    """Deterministically decomposes goals into executable sub-trees."""
    def decompose(self, goal: Goal, depth: int = 0, max_depth: int = 3) -> List[Goal]:
        if depth >= max_depth or goal.metadata.get("atomic", False):
            goal.metadata["atomic"] = True
            return [goal]

        subgoals = []
        steps = self._deterministic_split(goal.title, goal.description)
        for i, step in enumerate(steps):
            sid = hashlib.sha256(f"{goal.id}_sub_{i}_{depth}".encode()).hexdigest()[:12]
            sub = Goal(
                id=sid, title=f"{goal.title} :: Step {i+1}", description=step,
                importance=goal.importance * 0.9, urgency=goal.urgency,
                status=GoalStatus.NEW, origin=goal.origin, parent_goal=goal.id,
                dependencies=[goal.id] if i == 0 else [subgoals[-1].id],
                metadata={"atomic": depth == max_depth - 1}
            )
            subgoals.append(sub)
            goal.child_goals.append(sub.id)

        logger.info("Decomposed goal %s into %d subgoals (depth %d)", goal.id, len(subgoals), depth)
        all_nodes = [goal]
        for sg in subgoals:
            all_nodes.extend(self.decompose(sg, depth + 1, max_depth))
        return all_nodes

    def _deterministic_split(self, title: str, desc: str) -> List[str]:
        h = int(hashlib.md5(f"{title}_{desc}".encode()).hexdigest(), 16)
        count = 2 + (h % 3)
        return [f"Execute phase {i+1} of {title}" for i in range(count)]
