"""Replay Metrics Tracker: Stores aggregate statistics for the replay buffer."""
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ReplayMetrics:
    """Aggregate statistics for experience storage and replay."""
    total_stored: int = 0
    total_replayed: int = 0
    success_replays: int = 0
    failure_replays: int = 0
    avg_priority: float = 0.0
    compression_ratio: float = 1.0
    episodes_tracked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics to dictionary."""
        return {
            "total_stored": self.total_stored,
            "total_replayed": self.total_replayed,
            "success_replays": self.success_replays,
            "failure_replays": self.failure_replays,
            "avg_priority": round(self.avg_priority, 4),
            "compression_ratio": round(self.compression_ratio, 4),
            "episodes_tracked": self.episodes_tracked
        }
