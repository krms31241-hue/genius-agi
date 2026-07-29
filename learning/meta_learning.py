"""Meta Learning Engine: Strategy analysis, automatic ranking, adaptation tracking, and cross-system integration."""
import os
import json
import time
import tempfile
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class StrategyRecord:
    """Tracks performance, adaptation, and efficiency of a single execution strategy."""
    id: str
    name: str
    executions: int = 0
    successes: int = 0
    failures: int = 0
    total_duration: float = 0.0
    confidence_history: List[float] = field(default_factory=list)
    success_history: List[bool] = field(default_factory=list)
    adaptation_score: float = 0.0
    efficiency_score: float = 0.0
    confidence_improvement: float = 0.0
    failure_reduction: float = 0.0
    composite_score: float = 0.0
    last_used: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize strategy record to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyRecord":
        """Deserialize strategy record from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class MetaLearningEngine:
    """Production-grade meta-learning orchestrator.
    Analyzes historical executions, compares strategies, measures adaptation/efficiency,
    ranks alternatives, and integrates with Executive, Reasoning, Simulation, Counterfactual, and SkillLibrary."""
    
    def __init__(self, data_dir: str = "learning_data",
                 executive: Any = None, reasoner: Any = None,
                 simulator: Any = None, counterfactual: Any = None,
                 skill_library: Any = None) -> None:
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "meta_learning.json")
        self.strategies: Dict[str, StrategyRecord] = {}
        
        # Integration adapters
        self.executive = executive
        self.reasoner = reasoner
        self.simulator = simulator
        self.counterfactual = counterfactual
        self.skill_library = skill_library
        
        self._load()

    def record_execution(self, strategy_id: str, strategy_name: str,
                         success: bool, duration: float, confidence: float,
                         metadata: Optional[Dict[str, Any]] = None) -> StrategyRecord:
        """Record an execution outcome and update strategy metrics."""
        if strategy_id not in self.strategies:
            self.strategies[strategy_id] = StrategyRecord(id=strategy_id, name=strategy_name)
            
        rec = self.strategies[strategy_id]
        rec.executions += 1
        rec.total_duration += duration
        rec.last_used = time.time()
        if success: rec.successes += 1
        else: rec.failures += 1
        
        rec.confidence_history.append(confidence)
        rec.success_history.append(success)
        if metadata: rec.metadata.update(metadata)
        
        # Cap history windows for deterministic metric calculation
        rec.confidence_history = rec.confidence_history[-50:]
        rec.success_history = rec.success_history[-50:]
        
        self._compute_metrics(rec)
        self._save()
        return rec

    def _compute_metrics(self, rec: StrategyRecord) -> None:
        """Calculate adaptation, efficiency, confidence improvement, failure reduction, and composite score."""
        n = rec.executions
        if n == 0: return
        
        success_rate = rec.successes / n
        avg_duration = rec.total_duration / n
        
        # Efficiency: success rate normalized by duration (capped to prevent division by zero)
        rec.efficiency_score = round(success_rate / max(0.1, avg_duration), 4)
        
        # Adaptation & Failure Reduction (compare recent vs older window)
        window = min(10, len(rec.success_history))
        if window >= 4:
            mid = window // 2
            old_fails = sum(1 for s in rec.success_history[:mid] if not s)
            new_fails = sum(1 for s in rec.success_history[mid:] if not s)
            old_fail_rate = old_fails / mid
            new_fail_rate = new_fails / (window - mid)
            
            rec.failure_reduction = round(old_fail_rate - new_fail_rate, 4)
            rec.adaptation_score = round((1.0 - new_fail_rate) - (1.0 - old_fail_rate), 4)
        else:
            rec.adaptation_score = 0.0
            rec.failure_reduction = 0.0
            
        # Confidence Improvement
        if len(rec.confidence_history) >= 4:
            mid = len(rec.confidence_history) // 2
            old_conf = sum(rec.confidence_history[:mid]) / mid
            new_conf = sum(rec.confidence_history[mid:]) / (len(rec.confidence_history) - mid)
            rec.confidence_improvement = round(new_conf - old_conf, 4)
        else:
            rec.confidence_improvement = 0.0
            
        # Composite Score (weighted aggregation)
        rec.composite_score = round(
            (success_rate * 0.4) +
            (min(1.0, rec.efficiency_score) * 0.2) +
            (max(0.0, rec.adaptation_score) * 0.2) +
            (max(0.0, rec.confidence_improvement) * 0.1) +
            (max(0.0, rec.failure_reduction) * 0.1), 4
        )

    def rank_strategies(self) -> List[StrategyRecord]:
        """Return all strategies sorted by composite score (descending)."""
        return sorted(self.strategies.values(), key=lambda r: r.composite_score, reverse=True)

    def select_best_strategy(self, context: Optional[Dict[str, Any]] = None) -> Optional[StrategyRecord]:
        """Automatically select the highest-ranked strategy."""
        ranked = self.rank_strategies()
        return ranked[0] if ranked else None

    def analyze_with_integrations(self, strategy_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate enriched analysis using attached system adapters."""
        rec = self.strategies.get(strategy_id)
        if not rec:
            return {"error": "Strategy not found"}
            
        analysis = {"strategy_id": strategy_id, "metrics": rec.to_dict(), "insights": []}
        
        if self.skill_library:
            try:
                related = self.skill_library.search(query=rec.name)
                analysis["insights"].append(f"Found {len(related)} related skills in library.")
            except Exception: pass
            
        if self.reasoner:
            try:
                pred = self.reasoner.predict_effects(rec.name)
                analysis["insights"].append(f"Causal prediction: {len(pred.get('predicted_effects', []))} downstream effects.")
            except Exception: pass
            
        if self.simulator:
            analysis["insights"].append("Simulation engine attached for pre-flight strategy validation.")
            
        if self.counterfactual:
            analysis["insights"].append("Counterfactual engine attached for divergence analysis.")
            
        if self.executive:
            analysis["insights"].append("Executive engine attached for runtime alignment.")
            
        return analysis

    def _save(self) -> None:
        """Atomically persist strategy records to disk."""
        data = {"strategies": [s.to_dict() for s in self.strategies.values()]}
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, self.store_path)
        except Exception:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _load(self) -> None:
        """Restore strategy records from disk."""
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                for sd in data.get("strategies", []):
                    rec = StrategyRecord.from_dict(sd)
                    self.strategies[rec.id] = rec
            except Exception as e:
                logger.error("Failed to load meta learning state: %s", e)
