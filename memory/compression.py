"""Memory Compression Engine."""
import hashlib
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

class MemoryCompressor:
    """Removes duplicates, merges similar memories, and optimizes storage."""
    
    def __init__(self, similarity_threshold: float = 0.75):
        self.threshold = similarity_threshold

    def _tokenize(self, text: str) -> set:
        """Simple word tokenizer for similarity comparison."""
        return set(text.lower().split())

    def _calculate_similarity(self, set1: set, set2: set) -> float:
        """Calculate Sørensen-Dice similarity between two token sets.
        More robust than Jaccard for short text phrases and semantic overlap."""
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        total = len(set1) + len(set2)
        return (2.0 * intersection) / total if total > 0 else 0.0

    def find_duplicates(self, memories: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        """Find exact content duplicates via hash."""
        seen = {}
        duplicates = []
        for m in memories:
            content = m.get("content", "") or m.get("result", "") or ""
            h = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if h in seen:
                duplicates.append((seen[h], m.get("id", "")))
            else:
                seen[h] = m.get("id", "")
        return duplicates

    def find_similar(self, memories: List[Dict[str, Any]]) -> List[Tuple[str, str, float]]:
        """Find semantically similar memories above threshold."""
        similar = []
        for i, m1 in enumerate(memories):
            c1 = m1.get("content", "") or m1.get("result", "") or ""
            t1 = self._tokenize(c1)
            for j in range(i + 1, len(memories)):
                m2 = memories[j]
                c2 = m2.get("content", "") or m2.get("result", "") or ""
                t2 = self._tokenize(c2)
                sim = self._calculate_similarity(t1, t2)
                if sim >= self.threshold:
                    similar.append((m1["id"], m2["id"], sim))
        return similar

    def merge_records(self, base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two memory records, preserving highest confidence and union of tags."""
        merged = base.copy()
        merged["confidence"] = max(base.get("confidence", 0.5), incoming.get("confidence", 0.5))
        merged["frequency"] = base.get("frequency", 1) + incoming.get("frequency", 1)
        
        b_tags = set(base.get("tags", []))
        i_tags = set(incoming.get("tags", []))
        merged["tags"] = list(b_tags | i_tags)
        
        merged["updated_at"] = max(base.get("updated_at", 0), incoming.get("updated_at", 0))
        return merged

    def compress(self, memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run full compression analysis and return operations to perform."""
        duplicates = self.find_duplicates(memories)
        similar = self.find_similar(memories)
        
        ops = {
            "duplicates_to_remove": [d[1] for d in duplicates],
            "similar_pairs": similar,
            "space_saved_estimate": len(duplicates) + len(similar)
        }
        logger.info("Compression analysis: %d duplicates, %d similar pairs", len(duplicates), len(similar))
        return ops
