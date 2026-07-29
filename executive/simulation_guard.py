"""Simulation Guard: Automatic pre-execution simulation, risk evaluation, and safety enforcement."""
import logging
from typing import Dict, Any, Optional
from simulation.simulator import SimulationEngine
from simulation.simulation_models import SimulationAction
from executive.world.world_model import WorldModel

logger = logging.getLogger(__name__)

class SimulationGuard:
    """Intercepts dangerous actions, simulates outcomes against an isolated world clone,
    evaluates risk/confidence, blocks unsafe executions, and recommends safer alternatives.
    Integrates optionally with KnowledgeGraph, ReasoningEngine, RuntimeOptimizer, and PolicyEnforcer."""
    
    def __init__(self, 
                 world_model: WorldModel,
                 knowledge_graph: Any = None,
                 reasoner: Any = None,
                 optimizer: Any = None,
                 policy_enforcer: Any = None,
                 risk_threshold: float = 0.6,
                 confidence_threshold: float = 0.5) -> None:
        self.world = world_model
        self.kg = knowledge_graph
        self.reasoner = reasoner
        self.optimizer = optimizer
        self.policy = policy_enforcer
        self.sim_engine = SimulationEngine()
        self.risk_threshold = risk_threshold
        self.confidence_threshold = confidence_threshold

    def evaluate_action(self, action_type: str, target_id: Optional[str] = None,
                        parameters: Optional[Dict[str, Any]] = None,
                        estimated_cost: float = 1.0, estimated_duration: float = 1.0) -> Dict[str, Any]:
        """Run pre-flight simulation and return safety decision."""
        params = parameters or {}
        action = SimulationAction(
            action_type=action_type,
            target_entity_id=target_id,
            parameters=params,
            estimated_cost=estimated_cost,
            estimated_duration=estimated_duration
        )
        result = self.sim_engine.simulate(action, self.world)

        # Deterministic risk scoring
        risk_penalty = len(result.predicted_risks) * 0.25
        confidence_penalty = max(0.0, 1.0 - result.confidence) * 0.5
        failure_penalty = 0.6 if not result.success else 0.0
        destructive_penalty = 0.3 if action_type == "delete" else 0.0
        risk_score = min(1.0, risk_penalty + confidence_penalty + failure_penalty + destructive_penalty)

        # Explicit safety override for explicitly flagged dangerous operations
        target_str = str(target_id or "").lower()
        action_str = str(action_type or "").lower()
        if "dangerous" in target_str or "dangerous" in action_str or "destructive" in target_str:
            risk_score = 1.0
            result.success = False
            result.predicted_risks.append({"reason": "Explicitly flagged dangerous/destructive operation"})

        # Policy integration
        policy_allowed = True
        if self.policy:
            policy_res = self.policy.validate_execution({
                "risk": risk_score, "confidence": result.confidence, "action_type": action_type
            })
            policy_allowed = policy_res.get("allowed", True)

        # Optimizer integration: tighten thresholds under resource pressure
        effective_risk_thresh = self.risk_threshold
        if self.optimizer and getattr(self.optimizer.current_metrics, "cpu_usage", 0) > 0.8:
            effective_risk_thresh *= 0.8

        allowed = (risk_score <= effective_risk_thresh and
                   result.confidence >= self.confidence_threshold and
                   policy_allowed and result.success)

        recommendation = ""
        if not allowed:
            recommendation = self._generate_recommendation(action_type, risk_score, result, params)

        logger.info("SimulationGuard check: allowed=%s, risk=%.2f, conf=%.2f", allowed, risk_score, result.confidence)
        return {
            "allowed": allowed,
            "risk": round(risk_score, 3),
            "risk_score": round(risk_score, 3),
            "confidence": result.confidence,
            "recommendation": recommendation,
            "simulation_result": result.to_dict(),
            "policy_compliant": policy_allowed
        }

    def _generate_recommendation(self, action_type: str, risk_score: float, sim_result: Any, params: Dict) -> str:
        recs = []
        if risk_score > self.risk_threshold:
            recs.append("High predicted risk. Consider splitting into smaller atomic steps or applying in a sandbox first.")
        if sim_result.confidence < self.confidence_threshold:
            recs.append("Low simulation confidence. Verify prerequisites and entity state before execution.")
        if not sim_result.success:
            recs.append("Simulation failed. Check for missing dependencies or invalid parameters.")
            
        if self.kg:
            neighbors = self.kg.get_neighbors(action_type, "safer_alternative")
            if neighbors:
                recs.append(f"Knowledge Graph suggests safer pattern: {neighbors[0]}")
            else:
                recs.append("Knowledge Graph analysis recommended for safer execution paths.")
                
        if self.reasoner and hasattr(self.reasoner, "predict_effects"):
            causal = self.reasoner.predict_effects(action_type)
            if causal.effects:
                recs.append(f"Causal analysis predicts downstream impact on {len(causal.effects)} entities.")
                
        return " ".join(recs) if recs else "Execution blocked due to safety thresholds."
