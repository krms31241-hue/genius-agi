"""Runtime Optimizer: Monitors system metrics and automatically optimizes execution strategy."""
import time
import os
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class RuntimeMetrics:
    """Container for current runtime telemetry."""
    cpu_usage: float = 0.0          # 0.0 to 1.0
    memory_usage: float = 0.0       # 0.0 to 1.0
    avg_latency: float = 0.0        # seconds
    queue_depth: int = 0
    failure_rate: float = 0.0       # 0.0 to 1.0
    retry_rate: float = 0.0         # 0.0 to 1.0
    timestamp: float = field(default_factory=time.monotonic)

@dataclass
class OptimizationAction:
    """Represents a recommended or applied strategy change."""
    action_type: str
    target: str
    value: Any
    reason: str
    priority: int = 0  # 0=low, 10=critical

class RuntimeOptimizer:
    """Deterministic runtime optimizer that analyzes telemetry and adjusts execution parameters.
    Monitors CPU, Memory, Latency, Retries, Failures, and Queue Depth."""
    
    def __init__(self, 
                 cpu_threshold: float = 0.8,
                 memory_threshold: float = 0.8,
                 latency_threshold: float = 5.0,
                 failure_threshold: float = 0.2,
                 queue_threshold: int = 20):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.latency_threshold = latency_threshold
        self.failure_threshold = failure_threshold
        self.queue_threshold = queue_threshold
        
        self.current_metrics = RuntimeMetrics()
        self.history: List[RuntimeMetrics] = []
        self.lock = threading.RLock()
        self.recommendations: List[OptimizationAction] = []
        
        # Optimization State
        self.concurrency_modifier: float = 1.0
        self.backoff_modifier: float = 1.0
        self.strategy_mode: str = "balanced"  # balanced, conservative, aggressive

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Ingest new telemetry data."""
        with self.lock:
            self.current_metrics = RuntimeMetrics(
                cpu_usage=metrics.get("cpu_usage", self.current_metrics.cpu_usage),
                memory_usage=metrics.get("memory_usage", self.current_metrics.memory_usage),
                avg_latency=metrics.get("avg_latency", self.current_metrics.avg_latency),
                queue_depth=metrics.get("queue_depth", self.current_metrics.queue_depth),
                failure_rate=metrics.get("failure_rate", self.current_metrics.failure_rate),
                retry_rate=metrics.get("retry_rate", self.current_metrics.retry_rate)
            )
            self.history.append(self.current_metrics)
            # Keep history bounded
            if len(self.history) > 100:
                self.history = self.history[-50:]

    def analyze(self) -> List[OptimizationAction]:
        """Analyze current metrics and generate optimization recommendations."""
        with self.lock:
            self.recommendations = []
            m = self.current_metrics
            
            # 1. Resource Pressure (CPU/Memory) -> Throttle
            if m.cpu_usage > self.cpu_threshold or m.memory_usage > self.memory_threshold:
                self.recommendations.append(OptimizationAction(
                    action_type="throttle", target="concurrency", value=0.5,
                    reason=f"High resource usage (CPU: {m.cpu_usage:.2f}, Mem: {m.memory_usage:.2f})",
                    priority=9
                ))
                self.strategy_mode = "conservative"
            
            # 2. High Failure Rate -> Stabilize
            elif m.failure_rate > self.failure_threshold:
                self.recommendations.append(OptimizationAction(
                    action_type="stabilize", target="retries", value=2,
                    reason=f"High failure rate: {m.failure_rate:.2f}",
                    priority=8
                ))
                self.recommendations.append(OptimizationAction(
                    action_type="backoff", target="delay", value=2.0,
                    reason="Increasing backoff to reduce contention",
                    priority=7
                ))
                self.strategy_mode = "conservative"

            # 3. High Latency -> Optimize Path
            elif m.avg_latency > self.latency_threshold:
                self.recommendations.append(OptimizationAction(
                    action_type="optimize", target="critical_path", value=True,
                    reason=f"High average latency: {m.avg_latency:.2f}s",
                    priority=6
                ))
            
            # 4. Queue Depth High + Resources Low -> Accelerate
            elif m.queue_depth > self.queue_threshold and m.cpu_usage < 0.5 and m.memory_usage < 0.5:
                self.recommendations.append(OptimizationAction(
                    action_type="accelerate", target="concurrency", value=1.5,
                    reason=f"Queue depth high ({m.queue_depth}) with low resource usage",
                    priority=5
                ))
                self.strategy_mode = "aggressive"
            
            # 5. Default -> Balanced
            else:
                if self.strategy_mode != "balanced":
                    self.recommendations.append(OptimizationAction(
                        action_type="normalize", target="strategy", value="balanced",
                        reason="Metrics within normal parameters",
                        priority=1
                    ))
                self.strategy_mode = "balanced"

            return list(self.recommendations)

    def apply_optimizations(self, resource_mgr: Any = None, scheduler: Any = None) -> Dict[str, Any]:
        """Apply recommended optimizations to connected components."""
        applied = []
        for rec in self.recommendations:
            if rec.action_type == "throttle" and resource_mgr:
                # Reduce concurrency budget
                current = resource_mgr.budgets.get("max_concurrent", 4)
                new_val = max(1, int(current * rec.value))
                resource_mgr.budgets["max_concurrent"] = new_val
                applied.append(f"Reduced concurrency to {new_val}")
                
            elif rec.action_type == "accelerate" and resource_mgr:
                # Increase concurrency budget
                current = resource_mgr.budgets.get("max_concurrent", 4)
                new_val = min(16, int(current * rec.value))
                resource_mgr.budgets["max_concurrent"] = new_val
                applied.append(f"Increased concurrency to {new_val}")
                
            elif rec.action_type == "stabilize" and scheduler:
                # Adjust scheduler behavior (e.g., via metadata or specific attributes if supported)
                if hasattr(scheduler, 'metadata'):
                    scheduler.metadata["stabilization_mode"] = True
                applied.append("Enabled scheduler stabilization_mode")
                
            elif rec.action_type == "backoff":
                self.backoff_modifier = rec.value
                applied.append(f"Set backoff modifier to {rec.value}")
                
        return {"applied": applied, "mode": self.strategy_mode}

    def get_status(self) -> Dict[str, Any]:
        return {
            "metrics": self.current_metrics.__dict__,
            "strategy_mode": self.strategy_mode,
            "recommendations": [r.__dict__ for r in self.recommendations],
            "backoff_modifier": self.backoff_modifier
        }
