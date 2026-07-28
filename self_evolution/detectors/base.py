"""Base detector interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseDetector(ABC):
    name: str = "base"

    @abstractmethod
    def detect(self, file_map: Dict[str, Dict[str, Any]], dep_graph: Dict[str, Any], memory: Any) -> List[Dict[str, Any]]:
        """Return list of findings: {file, line, severity, reason, category}"""
        pass
