"""Policy Evolution Engine: Autonomous policy lifecycle orchestration."""
import os
import json
import time
import shutil
import tempfile
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from .policy import Policy
from .core_axioms import CoreAxiom
from .policy_generator import PolicyGenerator
from .policy_optimizer import PolicyOptimizer
from .policy_simulator import PolicySimulator
from .policy_validator import PolicyValidator
from .governance_manager import GovernanceManager

logger = logging.getLogger(__name__)

@dataclass
class EvolutionReport:
    cycle_id: str
    timestamp: float
    status: str
    promoted_policy: Optional[Dict[str, Any]] = None
    archived_policy: Optional[Dict[str, Any]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    comparison: Dict[str, Any] = field(default_factory=dict)
    reasoning: List[str] = field(default_factory=list)
    rollback_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class PolicyEvolutionEngine:
    """Autonomously evolves policies through generate→mutate→optimize→simulate→validate→compare→promote→archive."""
    
    def __init__(self, governance: GovernanceManager, evolution_dir: str = "governance_data/evolution"):
        self.governance = governance
        self.evolution_dir = os.path.abspath(evolution_dir)
        self.history_dir = os.path.join(self.evolution_dir, "history")
        self.metrics_dir = os.path.join(self.evolution_dir, "metrics")
        self.reports_dir = os.path.join(self.evolution_dir, "reports")
        for d in [self.history_dir, self.metrics_dir, self.reports_dir]:
            os.makedirs(d, exist_ok=True)
            
        self.generator = PolicyGenerator()
        self.optimizer = PolicyOptimizer()
        self.simulator = PolicySimulator()
        self.validator = PolicyValidator(axioms=governance.get_axioms())
        
    def run_cycle(self, context: Dict[str, Any] = None) -> EvolutionReport:
        context = context or {}
        cycle_id = f"evo_{int(time.time())}"
        reasoning = []
        
        try:
            # 1. Generate
            candidates = self.generator.generate(context)
            reasoning.append(f"Generated {len(candidates)} baseline candidates from telemetry")
            
            # 2 & 3. Mutate & Optimize
            optimized = []
            for base in candidates:
                optimized.extend(self.optimizer.optimize(base, context))
            reasoning.append(f"Optimized population: {len(optimized)} survivors")
            
            if not optimized:
                return self._fail_report(cycle_id, "No viable candidates after optimization", reasoning)
                
            # 4. Simulate
            sim_results = {}
            for p in optimized:
                sim_results[p.id] = self.simulator.simulate(p, context)
            reasoning.append("Simulation complete for all survivors")
            
            # 5. Validate
            valid_candidates = []
            for p in optimized:
                val = self.validator.validate(p, sim_results[p.id])
                if val["passed"]:
                    valid_candidates.append((p, sim_results[p.id]))
                else:
                    reasoning.append(f"Rejected {p.id}: {', '.join(val['reasons'])}")
                    
            if not valid_candidates:
                return self._fail_report(cycle_id, "All candidates failed validation", reasoning)
                
            # 6. Compare & Select Best
            valid_candidates.sort(key=lambda x: x[0].score, reverse=True)
            best_policy, best_metrics = valid_candidates[0]
            reasoning.append(f"Selected best candidate: {best_policy.id} (score: {best_policy.score:.2f})")
            
            # 7. Archive Previous & Promote
            active = self.governance.get_active_policies()
            archived = None
            rollback_info = {"previous_active": [], "snapshot_version": best_policy.version}
            
            if active:
                prev = active[0]
                archived = prev.to_dict()
                self.governance.disable_policy(prev.id)
                rollback_info["previous_active"].append(prev.id)
                reasoning.append(f"Archived previous active policy: {prev.id}")
                
            # Register forces status to draft internally; we activate immediately after
            self.governance.register_policy(best_policy)
            self.governance.enable_policy(best_policy.id)
            
            # Synchronize in-memory object state with governance lifecycle for accurate reporting
            best_policy.status = "active"
            best_policy.updated_at = time.time()
            
            reasoning.append(f"Promoted and activated policy: {best_policy.id}")
            
            # Persist
            report = EvolutionReport(
                cycle_id=cycle_id, timestamp=time.time(), status="success",
                promoted_policy=best_policy.to_dict(), archived_policy=archived,
                metrics=best_metrics, comparison={"score": best_policy.score, "alternatives": len(valid_candidates)-1},
                reasoning=reasoning, rollback_info=rollback_info
            )
            self._persist_report(report)
            self._persist_metrics(cycle_id, best_metrics)
            logger.info("Evolution cycle %s completed successfully", cycle_id)
            return report
            
        except Exception as e:
            logger.error("Evolution cycle %s failed: %s", cycle_id, e)
            return self._fail_report(cycle_id, str(e), reasoning)

    def _fail_report(self, cycle_id: str, error: str, reasoning: List[str]) -> EvolutionReport:
        reasoning.append(f"Cycle failed: {error}")
        return EvolutionReport(cycle_id=cycle_id, timestamp=time.time(), status="failed", reasoning=reasoning)

    def _persist_report(self, report: EvolutionReport):
        path = os.path.join(self.reports_dir, f"{report.cycle_id}.json")
        self._atomic_save(path, report.to_dict())

    def _persist_metrics(self, cycle_id: str, metrics: Dict[str, float]):
        path = os.path.join(self.metrics_dir, f"{cycle_id}.json")
        self._atomic_save(path, metrics)

    def _atomic_save(self, path: str, data: Any):
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)
            raise
