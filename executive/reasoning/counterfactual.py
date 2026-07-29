"""Counterfactual Reasoning Engine: Simulates alternate histories, compares outcomes, and generates explanations."""
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from simulation.simulator import SimulationEngine
from simulation.simulation_models import SimulationAction, SimulationPlan
from simulation.simulation_result import SimulationResult
from executive.world.world_model import WorldModel

logger = logging.getLogger(__name__)

@dataclass
class CounterfactualResult:
    """Structured output from counterfactual analysis."""
    hypothesis: str
    actual_outcome: Dict[str, Any]
    alternate_outcome: Dict[str, Any]
    delta: Dict[str, float]
    explanation: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "hypothesis": self.hypothesis,
            "actual_outcome": self.actual_outcome,
            "alternate_outcome": self.alternate_outcome,
            "delta": self.delta,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "metadata": self.metadata
        }

class CounterfactualEngine:
    """Production-grade counterfactual reasoning engine.
    Simulates alternate histories by applying hypothetical modifications to an isolated world clone,
    projects outcomes, computes metric deltas against actual history, and generates structured explanations."""
    
    def __init__(self, simulator: SimulationEngine, world_model: WorldModel) -> None:
        self.simulator = simulator
        self.world_model = world_model

    def analyze(self, hypothesis: str, setup_actions: List[SimulationAction],
                actual_metrics: Dict[str, Any], alternate_actions: Optional[List[SimulationAction]] = None) -> CounterfactualResult:
        """Evaluate a counterfactual hypothesis against actual historical metrics."""
        all_actions = list(setup_actions)
        if alternate_actions:
            all_actions.extend(alternate_actions)
            
        plan = SimulationPlan(actions=all_actions, metadata={"counterfactual": True, "hypothesis": hypothesis})
        sim_result = self.simulator.simulate(plan, self.world_model)
        
        alternate_metrics = self._extract_metrics(sim_result)
        delta = self._compute_delta(actual_metrics, alternate_metrics)
        explanation = self._generate_explanation(hypothesis, delta, sim_result)
        confidence = sim_result.confidence
        
        logger.info("Counterfactual analysis complete: '%s' | Confidence: %.2f", hypothesis, confidence)
        return CounterfactualResult(
            hypothesis=hypothesis,
            actual_outcome=actual_metrics,
            alternate_outcome=alternate_metrics,
            delta=delta,
            explanation=explanation,
            confidence=confidence
        )

    def _extract_metrics(self, result: SimulationResult) -> Dict[str, Any]:
        """Derive comparable metrics from a simulation result."""
        return {
            "success": result.success,
            "cost": result.estimated_cost,
            "duration": result.estimated_duration,
            "risk_count": len(result.predicted_risks),
            "confidence": result.confidence,
            "changes_count": len(result.predicted_changes)
        }

    def _compute_delta(self, actual: Dict[str, Any], alternate: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quantitative differences between actual and alternate outcomes."""
        delta = {}
        numeric_keys = ["cost", "duration", "risk_count", "confidence", "changes_count"]
        for key in numeric_keys:
            a_val = actual.get(key, 0.0)
            alt_val = alternate.get(key, 0.0)
            if isinstance(a_val, (int, float)) and isinstance(alt_val, (int, float)):
                delta[key] = round(alt_val - a_val, 4)
        delta["success_changed"] = 1.0 if alternate.get("success") != actual.get("success") else 0.0
        return delta

    def _generate_explanation(self, hypothesis: str, delta: Dict[str, float], sim_result: SimulationResult) -> str:
        """Generate a deterministic, structured explanation of the counterfactual divergence."""
        parts = [f"Under the hypothesis '{hypothesis}', the alternate outcome diverges from actual history."]
        
        if delta.get("success_changed"):
            status = "succeeded" if sim_result.success else "failed"
            parts.append(f"The operation would have {status}, changing the overall outcome.")
            
        significant_deltas = {k: v for k, v in delta.items() if k != "success_changed" and abs(v) > 0.01}
        if significant_deltas:
            impacts = []
            for k, v in significant_deltas.items():
                direction = "increased" if v > 0 else "decreased"
                impacts.append(f"{k} {direction} by {abs(v):.2f}")
            parts.append(f"Key metric shifts: {'; '.join(impacts)}.")
        else:
            parts.append("Quantitative metrics remained largely stable.")
            
        if sim_result.predicted_risks:
            parts.append(f"New risks identified: {len(sim_result.predicted_risks)}.")
            
        return " ".join(parts)
