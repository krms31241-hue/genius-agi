"""Decision Core Orchestrator - Safe AGI Architecture."""
import uuid
import time
from typing import Dict, Any, List, Optional
from .decision_models import Decision, Candidate
from .candidate_generator import CandidateGenerator
from .rule_engine import RuleEngine
from .risk_estimator import RiskEstimator
from .scorer import Scorer
from .evaluator import BenefitEvaluator, AlignmentEvaluator, CostEvaluator
from .consensus import ConsensusEngine
from .uncertainty import UncertaintyEstimator
from .confidence import ConfidenceEstimator
from .explanation import ExplanationEngine

class DecisionEngine:
    """Evaluates and ranks candidate decisions safely.
    NEVER executes commands, modifies files, or performs side effects.
    Integrates read-only with Memory, Laboratory, and Upgrade Manager."""
    
    def __init__(self, memory_adapter: Any = None, lab_adapter: Any = None, upgrade_adapter: Any = None):
        self.memory = memory_adapter
        self.lab = lab_adapter
        self.upgrade = upgrade_adapter
        
        self.generator = CandidateGenerator()
        self.rules = RuleEngine()
        self.risk_est = RiskEstimator()
        self.scorer = Scorer([BenefitEvaluator(), AlignmentEvaluator(), CostEvaluator()])
        self.consensus = ConsensusEngine()
        self.uncertainty_est = UncertaintyEstimator()
        self.confidence_est = ConfidenceEstimator()
        self.explainer = ExplanationEngine()

    def evaluate(self, goal: str, context: Dict[str, Any] = None) -> Decision:
        context = context or {}
        context["goal"] = goal
        
        candidates = self.generator.generate(goal, context)
        if len(candidates) < 2:
            candidates.append(Candidate(id="fallback", action="defer_action", description="Fallback defer", metadata={"strategy_type": "defer"}))
            
        evaluated = []
        for cand in candidates:
            rule_pass, violations = self.rules.validate(cand, context)
            if not rule_pass:
                evaluated.append({"candidate": cand, "valid": False, "violations": violations, "score": 0.0})
                continue
                
            scores = self.scorer.score_candidate(cand, context)
            risk = self.risk_est.estimate(cand, context)
            score_vals = list(scores.values())
            consensus_score = self.consensus.aggregate(score_vals)
            
            mem_rel = self._get_memory_relevance(goal, context)
            uncertainty = self.uncertainty_est.calculate(cand, score_vals, mem_rel)
            confidence = self.confidence_est.calculate(cand, risk["composite_risk"], uncertainty, rule_pass)
            reason = self.explainer.generate(cand, scores, risk, confidence, uncertainty, violations, consensus_score)
            
            evaluated.append({
                "candidate": cand, "valid": True, "violations": [],
                "scores": scores, "risk": risk, "consensus": consensus_score,
                "uncertainty": uncertainty, "confidence": confidence, "reason": reason
            })
            
        valid = [e for e in evaluated if e["valid"]]
        if not valid:
            fallback = candidates[-1]
            return Decision(
                decision=fallback.id,
                score=0.0, confidence=0.0, uncertainty=1.0, risk=1.0,
                reason=["All candidates violated hard constraints. Deferred."],
                alternatives=candidates[:-1],
                metadata={"timestamp": time.time(), "status": "deferred"}
            )
            
        valid.sort(key=lambda x: x["consensus"], reverse=True)
        best = valid[0]
        alternatives = [e["candidate"] for e in valid[1:]]
        
        return Decision(
            decision=best["candidate"].id,
            score=best["consensus"],
            confidence=best["confidence"],
            uncertainty=best["uncertainty"],
            risk=best["risk"]["composite_risk"],
            reason=best["reason"],
            alternatives=alternatives,
            metadata={"timestamp": time.time(), "all_scores": [e["consensus"] for e in valid]}
        )

    def _get_memory_relevance(self, goal: str, context: Dict[str, Any]) -> float:
        """Read-only integration with Memory Core."""
        if self.memory and hasattr(self.memory, "search_hybrid"):
            try:
                res = self.memory.search_hybrid(goal, [], top_k=1)
                return 0.8 if res else 0.4
            except Exception:
                pass
        return 0.5
