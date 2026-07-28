"""Generates multiple candidate decisions deterministically."""
import hashlib
from typing import List, Dict, Any
from .decision_models import Candidate

class CandidateGenerator:
    """Produces multiple candidate strategies for a given goal.
    Never returns a single option. Fully deterministic and side-effect free."""
    
    def generate(self, goal: str, context: Dict[str, Any]) -> List[Candidate]:
        strategies = [
            ("standard", f"execute_standard_procedure for {goal}"),
            ("conservative", f"apply_conservative_fix for {goal}"),
            ("experimental", f"run_experimental_optimization for {goal}"),
            ("defer", f"defer_action_and_monitor for {goal}")
        ]
        candidates = []
        for i, (stype, action) in enumerate(strategies):
            cid = hashlib.sha256(f"{goal}_{action}_{i}".encode()).hexdigest()[:12]
            candidates.append(Candidate(
                id=cid,
                action=action,
                description=f"Candidate strategy {i+1} targeting: {goal}",
                metadata={
                    "strategy_type": stype,
                    "context_snapshot": context.copy(),
                    "estimated_cost": [50, 30, 80, 10][i],
                    "irreversible": stype == "experimental"
                }
            ))
        return candidates
