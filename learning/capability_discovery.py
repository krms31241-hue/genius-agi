"""Capability Discovery Engine: Automatic detection, scoring, graph building, coverage analysis, and growth recommendations."""
import os
import json
import time
import tempfile
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CapabilityNode:
    """Represents a discovered capability with metadata, scoring, and dependencies."""
    id: str
    name: str
    cap_type: str  # skill, strategy, curriculum, transferred
    score: float = 0.0
    status: str = "active"
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CapabilityDiscoveryEngine:
    """Production-grade capability discovery orchestrator.
    Scans existing systems, detects gaps, builds dependency graphs, scores capabilities,
    analyzes coverage, and generates deterministic growth recommendations."""
    
    def __init__(self, data_dir: str = "learning_data", **adapters) -> None:
        self.adapters = adapters
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.report_path = os.path.join(self.data_dir, "learning_report.json")
        self.capabilities: Dict[str, CapabilityNode] = {}
        self.graph_adj: Dict[str, List[str]] = defaultdict(list)
        self.coverage_metrics: Dict[str, Any] = {}
        self.recommendations: List[Dict[str, Any]] = []

    def scan_capabilities(self) -> Dict[str, CapabilityNode]:
        """Aggregate capabilities from all attached learning & executive systems."""
        self.capabilities = {}
        
        # Skill Library
        skill_lib = self.adapters.get("skill_library")
        if skill_lib:
            for s in skill_lib.search():
                self.capabilities[s.id] = CapabilityNode(
                    id=s.id, name=s.name, cap_type="skill",
                    dependencies=s.dependencies, status=s.status,
                    metadata={"confidence": s.confidence, "success_rate": s.success_rate, "executions": s.execution_count}
                )
                
        # Meta Learning Strategies
        meta_eng = self.adapters.get("meta_learning")
        if meta_eng:
            for sid, rec in meta_eng.strategies.items():
                self.capabilities[f"strat_{sid}"] = CapabilityNode(
                    id=f"strat_{sid}", name=rec.name, cap_type="strategy",
                    status="active" if rec.composite_score > 0.3 else "deprecated",
                    metadata={"composite_score": rec.composite_score, "efficiency": rec.efficiency_score}
                )
                
        # Curriculum Mastered Tasks
        curriculum = self.adapters.get("curriculum")
        if curriculum:
            for tid, t in curriculum.tasks.items():
                if t.status == "mastered":
                    self.capabilities[f"curr_{tid}"] = CapabilityNode(
                        id=f"curr_{tid}", name=t.name, cap_type="curriculum",
                        dependencies=t.prerequisites, status="mastered",
                        metadata={"success_rate": t.success_rate, "attempts": t.attempts}
                    )
                    
        # Transfer Learning Records
        transfer = self.adapters.get("transfer_learning")
        if transfer:
            for tr in transfer.transfers:
                cap_id = f"trans_{tr.id}"
                self.capabilities[cap_id] = CapabilityNode(
                    id=cap_id, name=f"Transfer({tr.source_domain}->{tr.target_domain})",
                    cap_type="transferred", status="active" if tr.success else "failed",
                    metadata={"similarity": tr.similarity_score, "adapted_confidence": tr.adapted_confidence}
                )
                
        logger.info("Scanned %d capabilities across attached systems", len(self.capabilities))
        return self.capabilities

    def detect_gaps(self, required: List[str]) -> List[str]:
        """Identify missing capabilities by comparing required names against discovered capabilities."""
        existing_names = {c.name.lower() for c in self.capabilities.values()}
        existing_ids = {c.id.lower() for c in self.capabilities.values()}
        gaps = []
        for req in required:
            r_lower = req.lower()
            if r_lower not in existing_names and r_lower not in existing_ids:
                gaps.append(req)
        return gaps

    def build_capability_graph(self) -> Dict[str, List[str]]:
        """Construct a dependency graph linking capabilities."""
        self.graph_adj = defaultdict(list)
        for cid, cap in self.capabilities.items():
            for dep in cap.dependencies:
                if dep in self.capabilities:
                    self.graph_adj[dep].append(cid)
        logger.info("Built capability graph with %d nodes", len(self.capabilities))
        return dict(self.graph_adj)

    def score_capabilities(self) -> Dict[str, float]:
        """Compute deterministic scores for all discovered capabilities."""
        scores = {}
        for cid, cap in self.capabilities.items():
            meta = cap.metadata
            success = meta.get("success_rate", 0.5)
            conf = meta.get("confidence", meta.get("adapted_confidence", 0.5))
            count = meta.get("executions", meta.get("attempts", 1))
            mastery_bonus = 0.2 if cap.status == "mastered" else 0.0
            strat_bonus = meta.get("composite_score", 0.0) * 0.3 if cap.cap_type == "strategy" else 0.0
            
            score = min(1.0, (success * 0.4) + (conf * 0.3) + (min(1.0, count / 10.0) * 0.2) + mastery_bonus + strat_bonus)
            cap.score = round(score, 4)
            scores[cid] = cap.score
        return scores

    def analyze_coverage(self, required: List[str]) -> Dict[str, Any]:
        """Compute coverage percentage and identify critical missing capabilities."""
        gaps = self.detect_gaps(required)
        total = len(required)
        covered = total - len(gaps)
        coverage_pct = round((covered / max(1, total)) * 100, 2)
        
        self.coverage_metrics = {
            "total_required": total,
            "covered": covered,
            "missing": len(gaps),
            "coverage_percentage": coverage_pct,
            "gaps": gaps
        }
        return self.coverage_metrics

    def recommend_growth(self, required: List[str]) -> List[Dict[str, Any]]:
        """Generate deterministic growth recommendations based on gaps, scores, and system state."""
        self.recommendations = []
        gaps = self.detect_gaps(required)
        
        if not gaps:
            self.recommendations.append({"type": "maintenance", "target": "all", "reason": "Full coverage achieved. Focus on optimization and retention."})
            return self.recommendations
            
        for gap in gaps:
            rec = {"type": "acquisition", "target": gap, "reason": f"Missing required capability: {gap}", "priority": "high"}
            
            # Check if transfer learning can bridge the gap
            transfer = self.adapters.get("transfer_learning")
            if transfer and transfer.domains:
                domains = list(transfer.domains.keys())
                if len(domains) >= 2:
                    rec["suggestion"] = f"Explore cross-domain transfer from {domains[0]} to bridge {gap}"
                    
            # Check if curriculum can structure learning
            curriculum = self.adapters.get("curriculum")
            if curriculum:
                rec["suggestion"] = rec.get("suggestion", "") + " | Generate progressive curriculum path for structured mastery."
                
            # Check replay buffer for failure patterns
            replay = self.adapters.get("replay_buffer")
            if replay and replay.metrics.failure_replays > replay.metrics.success_replays:
                rec["priority"] = "critical"
                rec["reason"] += " High historical failure rate detected in related executions."
                
            self.recommendations.append(rec)
            
        # Low-score capability optimization
        low_scores = [cid for cid, s in self.score_capabilities().items() if s < 0.4]
        if low_scores:
            self.recommendations.append({
                "type": "optimization",
                "target": low_scores[:3],
                "reason": "Low-performing capabilities detected. Recommend meta-learning strategy rotation or experience replay fine-tuning.",
                "priority": "medium"
            })
            
        return self.recommendations

    def generate_report(self, required_capabilities: List[str], path: Optional[str] = None) -> Dict[str, Any]:
        """Orchestrate full discovery pipeline and persist learning_report.json."""
        self.scan_capabilities()
        self.build_capability_graph()
        self.score_capabilities()
        coverage = self.analyze_coverage(required_capabilities)
        recommendations = self.recommend_growth(required_capabilities)
        
        report = {
            "timestamp": time.time(),
            "capabilities_discovered": len(self.capabilities),
            "capability_graph": dict(self.graph_adj),
            "capability_scores": {cid: cap.score for cid, cap in self.capabilities.items()},
            "coverage_analysis": coverage,
            "recommendations": recommendations,
            "system_integration": {k: (v is not None) for k, v in self.adapters.items()}
        }
        
        save_path = path or self.report_path
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(save_path), suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(report, f, indent=2)
            shutil.move(tmp, save_path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)
            
        logger.info("Learning report generated and saved to %s", save_path)
        return report
