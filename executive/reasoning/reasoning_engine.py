"""Reasoning Engine: Orchestrates causal inference, explanation, and persistence."""
import logging
import json
import os
import tempfile
import shutil
from typing import Dict, Any, List, Optional, Set
from .causal_graph import CausalGraph
from .causal_chain import CausalChainBuilder
from .root_cause import RootCauseAnalyzer
from .effect_predictor import EffectPredictor
from .reasoning_models import CausalRelation, CausalType, ReasoningResult

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """Production-grade causal reasoning orchestrator."""
    def __init__(self, data_dir: str = "executive_data") -> None:
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_path = os.path.join(self.data_dir, "reasoning_state.json")
        
        self.graph = CausalGraph()
        self.builder = CausalChainBuilder(self.graph)
        self.root_analyzer = RootCauseAnalyzer(self.graph, self.builder)
        self.predictor = EffectPredictor(self.graph, self.builder)
        
        self._load_state()

    def register_relation(self, cause_id: str, effect_id: str, rel_type: str = CausalType.CAUSES,
                          confidence: float = 1.0, evidence: str = "") -> bool:
        """Add a causal relation to the knowledge base."""
        rel = CausalRelation(cause_id=cause_id, effect_id=effect_id, relation_type=rel_type,
                             confidence=confidence, evidence=evidence)
        success = self.graph.add_relation(rel)
        if success:
            self._save_state()
        return success

    def explain_why(self, effect_id: str, context: Optional[Dict[str, Any]] = None) -> ReasoningResult:
        """Answer: Why did X happen? Returns root causes and chains."""
        causes = self.root_analyzer.analyze([effect_id])
        chains = self.builder.trace_back(effect_id)
        
        explanation = f"Entity {effect_id} is likely caused by: "
        if causes:
            top = causes[0]
            explanation += f"{top['cause_id']} (score: {top['score']}). "
            explanation += "Evidence: " + "; ".join(top['explanations'][:2])
        else:
            explanation += "No known causal predecessors found."

        return ReasoningResult(
            query=f"Why did {effect_id} happen?",
            explanation=explanation,
            causes=causes,
            chains=chains,
            confidence=causes[0]["score"] if causes else 0.0,
            metadata={"context": context or {}}
        )

    def predict_effects(self, cause_id: str, context: Optional[Dict[str, Any]] = None) -> ReasoningResult:
        """Answer: What will happen if Z changes?"""
        prediction = self.predictor.predict(cause_id)
        impact = self.predictor.estimate_impact(cause_id)
        
        explanation = f"Changing {cause_id} will likely affect {len(prediction['predicted_effects'])} downstream entities. "
        if prediction['predicted_effects']:
            top = prediction['predicted_effects'][0]
            explanation += f"Highest impact on {top['entity_id']} (confidence: {top['confidence']})."
        
        return ReasoningResult(
            query=f"What happens if {cause_id} changes?",
            explanation=explanation,
            effects=prediction['predicted_effects'],
            confidence=prediction['predicted_effects'][0]['confidence'] if prediction['predicted_effects'] else 0.0,
            metadata={"impact_score": impact, "context": context or {}}
        )

    def what_depends_on(self, entity_id: str) -> List[str]:
        """Answer: What depends on this entity?"""
        return self.graph.adj.get(entity_id, [])

    def validate_integrity(self, valid_ids: Optional[Set[str]] = None) -> Dict[str, Any]:
        """Check graph integrity and cycles."""
        cycles = self.graph.detect_cycles()
        dangling = self.graph.validate_references(valid_ids) if valid_ids else []
        return {
            "cycles_detected": len(cycles),
            "cycles": cycles,
            "dangling_references": len(dangling),
            "dangling_details": dangling,
            "is_valid": len(cycles) == 0 and len(dangling) == 0
        }

    def serialize(self) -> Dict[str, Any]:
        return self.graph.to_dict()

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.graph = CausalGraph.from_dict(data)
        self.builder = CausalChainBuilder(self.graph)
        self.root_analyzer = RootCauseAnalyzer(self.graph, self.builder)
        self.predictor = EffectPredictor(self.graph, self.builder)

    def _save_state(self) -> None:
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(self.serialize(), f, indent=2)
            shutil.move(tmp, self.state_path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)

    def _load_state(self) -> None:
        if os.path.exists(self.state_path):
            try:
                with open(self.state_path, 'r') as f:
                    data = json.load(f)
                self.deserialize(data)
            except Exception as e:
                logger.error("Failed to load reasoning state: %s", e)
