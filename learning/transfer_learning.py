"""Transfer Learning Engine: Domain similarity, skill transfer, knowledge reuse, and cross-domain metrics."""
import os
import json
import time
import uuid
import tempfile
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional
from .skill import Skill
from .skill_library import SkillLibrary

logger = logging.getLogger(__name__)

@dataclass
class DomainProfile:
    """Represents a knowledge domain with feature tags for similarity computation."""
    id: str
    name: str
    features: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

@dataclass
class TransferRecord:
    """Tracks a single skill transfer event between domains."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_skill_id: str = ""
    source_domain: str = ""
    target_domain: str = ""
    similarity_score: float = 0.0
    adapted_confidence: float = 0.0
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransferRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class TransferLearningEngine:
    """Production-grade transfer learning orchestrator.
    Computes domain similarity, suggests cross-domain skill reuse, adapts transferred skills,
    scales confidence deterministically, and tracks transfer outcomes."""
    
    def __init__(self, skill_library: SkillLibrary, data_dir: str = "learning_data") -> None:
        self.skill_library = skill_library
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "transfer_learning.json")
        self.domains: Dict[str, DomainProfile] = {}
        self.transfers: List[TransferRecord] = []
        self._load()

    def register_domain(self, domain_id: str, name: str, features: List[str]) -> bool:
        """Register a knowledge domain with descriptive feature tags."""
        self.domains[domain_id] = DomainProfile(id=domain_id, name=name, features=features)
        self._save()
        return True

    def compute_similarity(self, domain_a_id: str, domain_b_id: str) -> float:
        """Compute Jaccard similarity between two domains based on feature overlap."""
        da = self.domains.get(domain_a_id)
        db = self.domains.get(domain_b_id)
        if not da or not db:
            return 0.0
        set_a = set(da.features)
        set_b = set(db.features)
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return round(intersection / union, 4) if union > 0 else 0.0

    def suggest_transfers(self, source_domain: str, target_domain: str, min_similarity: float = 0.3) -> List[Dict[str, Any]]:
        """Automatically suggest skills from source domain applicable to target domain."""
        sim = self.compute_similarity(source_domain, target_domain)
        if sim < min_similarity:
            return []
        
        source_skills = self.skill_library.search(category=source_domain)
        suggestions = []
        for s in source_skills:
            transfer_conf = round(s.confidence * sim, 4)
            suggestions.append({
                "skill_id": s.id,
                "skill_name": s.name,
                "source_confidence": s.confidence,
                "transfer_confidence": transfer_conf,
                "similarity": sim
            })
        return sorted(suggestions, key=lambda x: x["transfer_confidence"], reverse=True)

    def transfer_skill(self, skill_id: str, target_domain: str, adaptation_factor: float = 1.0) -> Optional[Skill]:
        """Adapt and register a source skill for a target domain with scaled confidence."""
        source_skill = self.skill_library.get_skill(skill_id)
        if not source_skill:
            return None
            
        source_domain = source_skill.category
        sim = self.compute_similarity(source_domain, target_domain)
        
        new_id = f"{skill_id}_t_{target_domain}"
        adapted_conf = min(1.0, round(source_skill.confidence * sim * adaptation_factor, 4))
        
        new_skill = Skill(
            id=new_id,
            name=f"{source_skill.name} (adapted for {target_domain})",
            version="1.0.0",
            description=f"Transferred from {source_domain}. Original: {source_skill.description}",
            category=target_domain,
            tags=source_skill.tags + [f"transferred_from_{source_domain}"],
            dependencies=source_skill.dependencies,
            metadata={
                "source_skill_id": skill_id, "source_domain": source_domain,
                "similarity": sim, "adaptation_factor": adaptation_factor
            },
            success_rate=source_skill.success_rate,
            execution_count=0,
            average_duration=source_skill.average_duration,
            confidence=adapted_conf
        )
        
        self.skill_library.add_skill(new_skill)
        
        record = TransferRecord(
            source_skill_id=skill_id,
            source_domain=source_domain,
            target_domain=target_domain,
            similarity_score=sim,
            adapted_confidence=adapted_conf
        )
        self.transfers.append(record)
        self._save()
        return new_skill

    def record_transfer_outcome(self, transfer_id: str, success: bool) -> bool:
        """Record whether a transferred skill succeeded or failed in the target domain."""
        for t in self.transfers:
            if t.id == transfer_id:
                t.success = success
                self._save()
                return True
        return False

    def get_cross_domain_metrics(self) -> Dict[str, Any]:
        """Aggregate statistics across all recorded transfers."""
        if not self.transfers:
            return {"total_transfers": 0, "success_rate": 0.0, "avg_similarity": 0.0, "avg_confidence_retention": 0.0}
            
        total = len(self.transfers)
        successes = sum(1 for t in self.transfers if t.success)
        avg_sim = sum(t.similarity_score for t in self.transfers) / total
        avg_conf = sum(t.adapted_confidence for t in self.transfers) / total
        
        return {
            "total_transfers": total,
            "success_rate": round(successes / total, 4),
            "avg_similarity": round(avg_sim, 4),
            "avg_confidence_retention": round(avg_conf, 4)
        }

    def _save(self) -> None:
        data = {
            "domains": [d.to_dict() for d in self.domains.values()],
            "transfers": [t.to_dict() for t in self.transfers]
        }
        fd, tmp = tempfile.mkstemp(dir=self.data_dir, suffix=".tmp")
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            shutil.move(tmp, self.store_path)
        except Exception:
            if os.path.exists(tmp): os.remove(tmp)

    def _load(self) -> None:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, 'r') as f:
                    data = json.load(f)
                for dd in data.get("domains", []):
                    d = DomainProfile.from_dict(dd)
                    self.domains[d.id] = d
                for td in data.get("transfers", []):
                    self.transfers.append(TransferRecord.from_dict(td))
            except Exception as e:
                logger.error("Failed to load transfer learning state: %s", e)
