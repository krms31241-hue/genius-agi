"""Replay Buffer: Prioritized storage, sampling strategies, compression, and persistence."""
import os
import json
import time
import tempfile
import shutil
import logging
import random
from typing import Dict, List, Any, Optional
from collections import defaultdict
from .experience import Experience
from .replay_metrics import ReplayMetrics

logger = logging.getLogger(__name__)

class ReplayBuffer:
    """Production-grade experience replay buffer with capacity management,
    time-decayed prioritization, episode grouping, and atomic JSON persistence."""
    
    def __init__(self, capacity: int = 1000, data_dir: str = "learning_data") -> None:
        self.capacity = capacity
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "replay_buffer.json")
        self.experiences: Dict[str, Experience] = {}
        self.episodes: Dict[str, List[str]] = defaultdict(list)
        self.metrics = ReplayMetrics()
        self._load()

    def store(self, exp: Experience) -> bool:
        """Store an experience. Triggers compression if capacity exceeded."""
        self.experiences[exp.id] = exp
        self.episodes[exp.episode_id].append(exp.id)
        self.metrics.total_stored += 1
        self.metrics.episodes_tracked = len(self.episodes)
        
        if len(self.experiences) > self.capacity:
            self._compress()
            
        self._save()
        return True

    def sample_random(self, n: int) -> List[Experience]:
        """Uniform random sampling."""
        ids = list(self.experiences.keys())
        if not ids: return []
        chosen = random.sample(ids, min(n, len(ids)))
        self._record_replay(chosen)
        return [self.experiences[i] for i in chosen]

    def sample_prioritized(self, n: int, decay_factor: float = 0.99) -> List[Experience]:
        """Sample top N experiences by time-decayed priority."""
        now = time.time()
        scored = []
        for exp in self.experiences.values():
            age_hours = (now - exp.timestamp) / 3600.0
            decayed_priority = exp.priority * (decay_factor ** age_hours)
            scored.append((decayed_priority, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        chosen = [exp for _, exp in scored[:n]]
        self._record_replay([e.id for e in chosen])
        return chosen

    def sample_success(self, n: int) -> List[Experience]:
        """Random sampling restricted to successful experiences."""
        successes = [e for e in self.experiences.values() if e.success]
        chosen = random.sample(successes, min(n, len(successes))) if successes else []
        self._record_replay([e.id for e in chosen])
        return chosen

    def sample_failure(self, n: int) -> List[Experience]:
        """Random sampling restricted to failed experiences."""
        failures = [e for e in self.experiences.values() if not e.success]
        chosen = random.sample(failures, min(n, len(failures))) if failures else []
        self._record_replay([e.id for e in chosen])
        return chosen

    def get_episode(self, episode_id: str) -> List[Experience]:
        """Retrieve all experiences belonging to a specific episode."""
        ids = self.episodes.get(episode_id, [])
        return [self.experiences[i] for i in ids if i in self.experiences]

    def _compress(self) -> None:
        """Reduce buffer size by retaining highest priority experiences."""
        if not self.experiences: return
        sorted_exps = sorted(self.experiences.values(), key=lambda e: e.priority, reverse=True)
        keep = sorted_exps[:self.capacity // 2]
        keep_ids = {e.id for e in keep}
        self.experiences = {e.id: e for e in keep}
        
        for eid in list(self.episodes.keys()):
            self.episodes[eid] = [i for i in self.episodes[eid] if i in keep_ids]
            if not self.episodes[eid]:
                del self.episodes[eid]
                
        self.metrics.compression_ratio = len(self.experiences) / max(1, self.metrics.total_stored)
        logger.info("Buffer compressed to %d experiences", len(self.experiences))

    def _record_replay(self, ids: List[str]) -> None:
        """Update replay statistics."""
        self.metrics.total_replayed += len(ids)
        total_p = 0.0
        for i in ids:
            exp = self.experiences.get(i)
            if exp:
                if exp.success: self.metrics.success_replays += 1
                else: self.metrics.failure_replays += 1
                total_p += exp.priority
                
        if self.metrics.total_replayed > 0:
            prev_count = self.metrics.total_replayed - len(ids)
            self.metrics.avg_priority = ((self.metrics.avg_priority * prev_count) + total_p) / self.metrics.total_replayed

    def _save(self) -> None:
        data = {
            "experiences": [e.to_dict() for e in self.experiences.values()],
            "episodes": dict(self.episodes),
            "metrics": self.metrics.to_dict()
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
                for ed in data.get("experiences", []):
                    exp = Experience.from_dict(ed)
                    self.experiences[exp.id] = exp
                    self.episodes[exp.episode_id].append(exp.id)
                m_data = data.get("metrics", {})
                self.metrics = ReplayMetrics(**{k: v for k, v in m_data.items() if k in ReplayMetrics.__dataclass_fields__})
            except Exception as e:
                logger.error("Failed to load replay buffer: %s", e)
