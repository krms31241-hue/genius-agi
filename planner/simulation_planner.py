"""Simulation Planner: Generates multiple futures, simulates outcomes, scores them, and compares alternatives."""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from simulation.simulator import SimulationEngine
from simulation.simulation_models import SimulationPlan, SimulationAction
from simulation.simulation_result import SimulationResult
from executive.world.world_model import WorldModel

logger = logging.getLogger(__name__)

@dataclass
class PlanEvaluation:
    """Stores simulation result and computed scores for a single plan."""
    plan_id: str
    result: SimulationResult
    scores: Dict[str, float]
    composite_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "composite_score": self.composite_score,
            "scores": self.scores,
            "success": self.result.success,
            "confidence": self.result.confidence
        }

@dataclass
class WhatIfResult:
    """Comparative analysis of multiple simulated futures."""
    evaluations: List[PlanEvaluation]
    best_plan: Optional[PlanEvaluation]
    worst_plan: Optional[PlanEvaluation]
    highest_reward: Optional[PlanEvaluation]
    lowest_risk: Optional[PlanEvaluation]
    highest_confidence: Optional[PlanEvaluation]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluations": [e.to_dict() for e in self.evaluations],
            "best_plan": self.best_plan.plan_id if self.best_plan else None,
            "worst_plan": self.worst_plan.plan_id if self.worst_plan else None,
            "highest_reward": self.highest_reward.plan_id if self.highest_reward else None,
            "lowest_risk": self.lowest_risk.plan_id if self.lowest_risk else None,
            "highest_confidence": self.highest_confidence.plan_id if self.highest_confidence else None,
            "metadata": self.metadata
        }

class SimulationPlanner:
    """Deterministic what-if planner that simulates multiple action sequences,
    scores them across multiple dimensions, and ranks outcomes."""
    
    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        self.engine = SimulationEngine()
        self.weights = weights or {
            "goal_alignment": 0.30,
            "resource_usage": 0.15,
            "risk": 0.25,
            "execution_time": 0.10,
            "success_probability": 0.20
        }

    def evaluate_futures(self, plans: List[Union[SimulationPlan, List[SimulationAction]]],
                         world_model: WorldModel,
                         goal_context: Optional[Dict[str, Any]] = None) -> WhatIfResult:
        """Simulate multiple plans against an isolated world clone and compare outcomes."""
        if not plans:
            return WhatIfResult([], None, None, None, None, None)

        evaluations: List[PlanEvaluation] = []
        for plan in plans:
            sim_plan = SimulationPlan(actions=plan) if isinstance(plan, list) else plan
            result = self.engine.simulate(sim_plan, world_model)
            eval_obj = self._score_plan(sim_plan, result, goal_context or {})
            evaluations.append(eval_obj)

        return self._compare_evaluations(evaluations)

    def _score_plan(self, plan: SimulationPlan, result: SimulationResult, context: Dict[str, Any]) -> PlanEvaluation:
        """Compute raw scores for a single simulated plan."""
        success_prob = result.confidence if result.success else 0.0
        risk_penalty = min(1.0, len(result.predicted_risks) * 0.2)
        risk_score = max(0.0, 1.0 - risk_penalty)
        goal_align = plan.metadata.get("goal_alignment", context.get("default_goal_alignment", 0.5))

        scores = {
            "goal_alignment": goal_align,
            "resource_usage": result.estimated_cost,  # Raw cost, inverted during normalization
            "risk": risk_score,
            "execution_time": result.estimated_duration,  # Raw duration, inverted during normalization
            "success_probability": success_prob
        }
        return PlanEvaluation(plan_id=plan.id, result=result, scores=scores, composite_score=0.0)

    def _compare_evaluations(self, evaluations: List[PlanEvaluation]) -> WhatIfResult:
        """Normalize scores, compute composites, and identify optimal/suboptimal plans."""
        if not evaluations:
            return WhatIfResult([], None, None, None, None, None)

        # Determine normalization bounds
        max_cost = max((e.scores["resource_usage"] for e in evaluations), default=1.0)
        max_cost = max_cost if max_cost > 0 else 1.0
        max_time = max((e.scores["execution_time"] for e in evaluations), default=1.0)
        max_time = max_time if max_time > 0 else 1.0

        for e in evaluations:
            # Invert cost/time: lower is better -> higher score
            e.scores["resource_usage"] = round(max(0.0, 1.0 - (e.scores["resource_usage"] / max_cost)), 4)
            e.scores["execution_time"] = round(max(0.0, 1.0 - (e.scores["execution_time"] / max_time)), 4)

            # Weighted composite
            composite = sum(e.scores[k] * self.weights.get(k, 0.0) for k in self.weights)
            e.composite_score = round(composite, 4)

        # Deterministic tie-breaking by plan_id
        best = max(evaluations, key=lambda e: (e.composite_score, e.plan_id))
        worst = min(evaluations, key=lambda e: (e.composite_score, e.plan_id))
        highest_reward = max(evaluations, key=lambda e: (e.scores["goal_alignment"] * e.scores["success_probability"], e.plan_id))
        lowest_risk = max(evaluations, key=lambda e: (e.scores["risk"], e.plan_id))
        highest_conf = max(evaluations, key=lambda e: (e.scores["success_probability"], e.plan_id))

        logger.info("What-if planning complete: %d futures evaluated. Best: %s, Worst: %s",
                    len(evaluations), best.plan_id, worst.plan_id)

        return WhatIfResult(
            evaluations=evaluations,
            best_plan=best,
            worst_plan=worst,
            highest_reward=highest_reward,
            lowest_risk=lowest_risk,
            highest_confidence=highest_conf
        )
