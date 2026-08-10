"""Memory Manager - Long-term and working memory for AGI"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class MemoryManager:
    """Manages short-term, long-term, and episodic memory"""
    
    def __init__(self, storage_dir: str = "memory_data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.working_memory: Dict[str, Any] = {}  # Short-term
        self.facts: List[Dict] = []  # Long-term facts
        self.episodes: List[Dict] = []  # Episodic memory
        self.patterns: Dict[str, int] = {}  # Pattern recognition
        
        self._load_memory()
    
    def set_working(self, key: str, value: Any) -> None:
        """Set working memory (short-term)"""
        self.working_memory[key] = value
    
    def get_working(self, key: str) -> Optional[Any]:
        """Get from working memory"""
        return self.working_memory.get(key)
    
    def add_fact(self, fact: str, metadata: Dict = None) -> None:
        """Add a fact to long-term memory"""
        entry = {
            "fact": fact,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "importance": 0.5
        }
        self.facts.append(entry)
        if len(self.facts) > 1000:
            self.facts = self.facts[-1000:]  # Keep last 1000
    
    def add_episode(self, prompt: str, response: str, metadata: Dict = None) -> None:
        """Record an interaction episode"""
        entry = {
            "prompt": prompt,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.episodes.append(entry)
        if len(self.episodes) > 500:
            self.episodes = self.episodes[-500:]
    
    def search_facts(self, query: str) -> List[Dict]:
        """Search facts matching query"""
        results = []
        query_lower = query.lower()
        for fact in self.facts:
            if query_lower in fact["fact"].lower():
                results.append(fact)
        return results[:10]  # Return top 10
    
    def record_pattern(self, pattern: str) -> None:
        """Record a recognized pattern"""
        self.patterns[pattern] = self.patterns.get(pattern, 0) + 1
    
    def _load_memory(self) -> None:
        """Load memory from disk"""
        facts_file = self.storage_dir / "facts.json"
        if facts_file.exists():
            try:
                with open(facts_file) as f:
                    self.facts = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load facts: {e}")
    
    def close(self) -> None:
        """Save memory to disk"""
        facts_file = self.storage_dir / "facts.json"
        try:
            with open(facts_file, 'w') as f:
                json.dump(self.facts, f)
        except Exception as e:
            logger.error(f"Could not save facts: {e}")
