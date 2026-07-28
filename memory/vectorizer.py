"""Deterministic Semantic Vector Representation."""
import hashlib
import math
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MemoryVectorizer:
    """Generates deterministic fixed-size vectors from text using feature hashing.
    No external AI models. Fully reproducible."""
    
    def __init__(self, dimension: int = 64):
        self.dim = dimension

    def _hash_token(self, token: str) -> int:
        """Deterministic hash for token indexing."""
        return int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)

    def vectorize(self, text: str) -> List[float]:
        """Convert text to normalized frequency vector."""
        vec = [0.0] * self.dim
        if not text:
            return vec
        
        tokens = text.lower().split()
        for token in tokens:
            h = self._hash_token(token)
            idx = h % self.dim
            vec[idx] += 1.0
            
        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Cosine similarity between two vectors."""
        if len(vec1) != len(vec2) or not vec1 or not vec2:
            return 0.0
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))

    def batch_vectorize(self, texts: List[str]) -> List[List[float]]:
        """Vectorize multiple texts."""
        return [self.vectorize(t) for t in texts]
