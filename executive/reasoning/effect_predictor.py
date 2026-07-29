"""Effect Predictor: Forecasts consequences and risk propagation."""
import logging
from typing import Dict, Any, List, Set
from collections import defaultdict
from .causal_graph import CausalGraph
from .causal_chain import CausalChainBuilder
from .reasoning_models import CausalType

logger = logging.getLogger(__name__)

class EffectPredictor:
    """Predicts direct and indirect effects of state changes or events."""
    def __init__(self, graph: CausalGraph, chain_builder: CausalChainBuilder) -> None:
        self.graph = graph
        self.builder = chain_builder

    def predict(self, cause_id: str, max_depth: int = 5) -> Dict[str, Any]:
        """Predict downstream effects, confidence, and impact."""
        chains = self.builder.trace_forward(cause_id, max_depth)
        effects: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"confidence": 0.0, "paths": 0, "risk": "low"})
        
        for chain in chains:
            for node in chain.nodes[1:]:
                effects[node]["confidence"] = max(effects[node]["confidence"], chain.confidence)
                effects[node]["paths"] += 1
                if chain.confidence > 0.7:
                    effects[node]["risk"] = "high"
                elif chain.confidence > 0.4:
                    effects[node]["risk"] = "medium"

        predicted = []
        for eid, data in effects.items():
            predicted.append({
                "entity_id": eid,
                "confidence": round(data["confidence"], 3),
                "path_count": data["paths"],
                "risk_level": data["risk"]
            })
        
        predicted.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "cause_id": cause_id,
            "predicted_effects": predicted,
            "total_chains": len(chains),
            "max_depth_reached": max_depth
        }

    def estimate_impact(self, cause_id: str, base_impact: float = 1.0) -> float:
        """Estimate total propagated impact score."""
        preds = self.predict(cause_id)
        total_impact = base_impact
        for eff in preds["predicted_effects"]:
            total_impact += base_impact * eff["confidence"] * 0.5
        return round(total_impact, 3)
