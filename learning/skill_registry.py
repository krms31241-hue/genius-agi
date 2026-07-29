"""Skill Registry: In-memory lookup, dependency graph, duplicate detection, and search."""
import logging
from typing import Dict, List, Optional, Set
from collections import defaultdict
from .skill import Skill

logger = logging.getLogger(__name__)

class SkillRegistry:
    """Manages skill indexing, dependency topology, and semantic duplicate prevention."""
    
    def __init__(self) -> None:
        self.skills: Dict[str, Skill] = {}
        self.dep_graph: Dict[str, List[str]] = defaultdict(list)
        self.rev_dep_graph: Dict[str, List[str]] = defaultdict(list)
        self.content_hashes: Dict[str, str] = {}  # hash -> skill_id

    def register(self, skill: Skill) -> bool:
        """Register a skill. Returns False if ID exists or semantic duplicate detected."""
        if skill.id in self.skills:
            return False
        h = skill.content_hash()
        if h in self.content_hashes:
            logger.warning("Duplicate skill detected: %s matches %s", skill.id, self.content_hashes[h])
            return False
        
        self.skills[skill.id] = skill
        self.content_hashes[h] = skill.id
        
        for dep in skill.dependencies:
            self.dep_graph[skill.id].append(dep)
            self.rev_dep_graph[dep].append(skill.id)
        return True

    def get(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def search(self, query: str = "", category: str = "", tags: Optional[List[str]] = None) -> List[Skill]:
        """Search active skills by name/description, category, and tags."""
        results = []
        q_lower = query.lower()
        t_set = set(tags or [])
        for s in self.skills.values():
            if s.status != "active":
                continue
            if category and s.category != category:
                continue
            if t_set and not t_set.issubset(set(s.tags)):
                continue
            if q_lower and q_lower not in s.name.lower() and q_lower not in s.description.lower():
                continue
            results.append(s)
        return results

    def get_dependencies(self, skill_id: str) -> List[str]:
        return self.dep_graph.get(skill_id, [])

    def get_dependents(self, skill_id: str) -> List[str]:
        return self.rev_dep_graph.get(skill_id, [])

    def validate_dependencies(self) -> List[str]:
        """Check for dangling dependency references."""
        issues = []
        for sid, deps in self.dep_graph.items():
            for d in deps:
                if d not in self.skills:
                    issues.append(f"Skill {sid} depends on missing skill {d}")
        return issues

    def remove(self, skill_id: str) -> bool:
        if skill_id not in self.skills:
            return False
        s = self.skills.pop(skill_id)
        self.content_hashes.pop(s.content_hash(), None)
        self.dep_graph.pop(skill_id, None)
        self.rev_dep_graph.pop(skill_id, None)
        return True
