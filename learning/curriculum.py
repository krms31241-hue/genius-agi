"""Curriculum Learning Engine: Progressive task ordering, mastery tracking, and automatic path generation."""
import os
import json
import time
import uuid
import tempfile
import shutil
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class CurriculumTask:
    """Represents a learnable unit with prerequisites, difficulty, and mastery tracking."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    base_difficulty: float = 1.0
    prerequisites: List[str] = field(default_factory=list)
    mastery_threshold: float = 0.8
    min_attempts: int = 3
    attempts: int = 0
    successes: int = 0
    success_rate: float = 0.0
    status: str = "pending"  # pending, active, mastered, failed
    last_attempt: float = 0.0
    next_retry: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurriculumTask":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

class CurriculumEngine:
    """Production-grade curriculum orchestrator.
    Generates progressive learning paths, tracks mastery, schedules retries,
    and optimizes sequencing based on performance."""
    
    def __init__(self, data_dir: str = "learning_data") -> None:
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)
        self.store_path = os.path.join(self.data_dir, "curriculum.json")
        self.tasks: Dict[str, CurriculumTask] = {}
        self.path: List[str] = []
        self._load()

    def add_task(self, task: CurriculumTask) -> bool:
        """Register a new learnable task."""
        self.tasks[task.id] = task
        self._save()
        return True

    def estimate_difficulty(self, task_id: str) -> float:
        """Compute effective difficulty based on base difficulty and dependency depth."""
        task = self.tasks.get(task_id)
        if not task: return 0.0
        depth = self._get_dependency_depth(task_id)
        return round(task.base_difficulty * (1 + depth * 0.2), 4)

    def _get_dependency_depth(self, task_id: str, visited: Optional[set] = None) -> int:
        if visited is None: visited = set()
        if task_id in visited: return 0
        visited.add(task_id)
        task = self.tasks.get(task_id)
        if not task or not task.prerequisites: return 0
        depths = [self._get_dependency_depth(p, visited) for p in task.prerequisites if p in self.tasks]
        return 1 + max(depths) if depths else 0

    def generate_curriculum(self, target_id: str) -> List[str]:
        """Automatically generate a progressive learning path to a target skill."""
        if target_id not in self.tasks:
            return []
            
        required = set()
        queue = [target_id]
        while queue:
            curr = queue.pop(0)
            if curr in required: continue
            required.add(curr)
            t = self.tasks.get(curr)
            if t:
                queue.extend(t.prerequisites)
                
        subset = {tid: self.tasks[tid] for tid in required if tid in self.tasks}
        self.path = self._topological_sort(subset)
        self._save()
        return self.path

    def _topological_sort(self, subset: Dict[str, CurriculumTask]) -> List[str]:
        """Deterministic topological sort ordered by effective difficulty."""
        in_degree = {tid: 0 for tid in subset}
        adj = {tid: [] for tid in subset}
        for tid, t in subset.items():
            for p in t.prerequisites:
                if p in subset:
                    adj[p].append(tid)
                    in_degree[tid] += 1
                    
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        queue.sort(key=lambda x: self.estimate_difficulty(x))
        
        result = []
        while queue:
            node = queue.pop(0)
            result.append(node)
            neighbors = sorted(adj[node], key=lambda x: self.estimate_difficulty(x))
            for n in neighbors:
                in_degree[n] -= 1
                if in_degree[n] == 0:
                    queue.append(n)
            queue.sort(key=lambda x: self.estimate_difficulty(x))
        return result

    def record_attempt(self, task_id: str, success: bool) -> None:
        """Record execution outcome, update mastery, and schedule retries."""
        task = self.tasks.get(task_id)
        if not task: return
        
        task.attempts += 1
        if success: task.successes += 1
        task.success_rate = task.successes / task.attempts
        task.last_attempt = time.time()
        
        if task.success_rate >= task.mastery_threshold and task.attempts >= task.min_attempts:
            task.status = "mastered"
        elif not success:
            task.status = "active"
            # Exponential backoff retry scheduling
            delay = 60 * (2 ** (task.attempts - 1))
            task.next_retry = time.time() + delay
        else:
            task.status = "active"
        self._save()

    def get_next_task(self) -> Optional[CurriculumTask]:
        """Retrieve the next actionable task respecting prerequisites and retry windows."""
        now = time.time()
        for tid in self.path:
            t = self.tasks.get(tid)
            if not t or t.status == "mastered": continue
            if t.next_retry > now: continue
            
            prereqs_met = all(
                self.tasks[p].status == "mastered" 
                for p in t.prerequisites if p in self.tasks
            )
            if prereqs_met:
                return t
        return None

    def optimize(self) -> List[str]:
        """Reorder and prune curriculum based on current mastery state."""
        unmastered = [tid for tid in self.path if self.tasks.get(tid).status != "mastered"]
        if not unmastered:
            self.path = []
            self._save()
            return []
            
        new_path = []
        for target in unmastered:
            new_path.extend(self.generate_curriculum(target))
            
        seen = set()
        ordered = [x for x in new_path if not (x in seen or seen.add(x))]
        
        # Filter out mastered tasks from the optimized path to focus on remaining work
        self.path = [x for x in ordered if self.tasks.get(x).status != "mastered"]
        self._save()
        return self.path

    def get_learning_path(self) -> List[Dict[str, Any]]:
        """Return structured representation of the current learning path."""
        return [self.tasks[tid].to_dict() for tid in self.path if tid in self.tasks]

    def _save(self) -> None:
        data = {
            "tasks": [t.to_dict() for t in self.tasks.values()],
            "path": self.path
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
                for td in data.get("tasks", []):
                    task = CurriculumTask.from_dict(td)
                    self.tasks[task.id] = task
                self.path = data.get("path", [])
            except Exception as e:
                logger.error("Failed to load curriculum: %s", e)
