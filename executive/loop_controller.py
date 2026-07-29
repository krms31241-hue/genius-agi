"""Loop Controller: Manages lifecycle, limits, watchdog, and statistics for the autonomous loop."""
import time
import threading
import logging
from typing import Dict, Any
from .loop_state import LoopState, LoopStatus

logger = logging.getLogger(__name__)

class LoopController:
    """Thread-safe controller enforcing iteration limits, duration limits, failure thresholds, and watchdog timeouts."""
    def __init__(self, max_iterations: int = 100, max_duration_sec: float = 3600.0,
                 max_consecutive_failures: int = 5, watchdog_timeout_sec: float = 30.0):
        self.max_iterations = max_iterations
        self.max_duration_sec = max_duration_sec
        self.max_consecutive_failures = max_consecutive_failures
        self.watchdog_timeout_sec = watchdog_timeout_sec
        self.lock = threading.RLock()
        self._phase_start_time: float = 0.0

    def start(self, state: LoopState) -> bool:
        with self.lock:
            if state.status not in (LoopStatus.IDLE, LoopStatus.PAUSED):
                return False
            state.status = LoopStatus.RUNNING
            state.started_at = state.started_at or time.monotonic()
            state.updated_at = time.monotonic()
            logger.info("Loop controller started")
            return True

    def stop(self, state: LoopState) -> None:
        with self.lock:
            state.stop_requested = True
            state.status = LoopStatus.STOPPED
            state.updated_at = time.monotonic()
            logger.info("Loop controller stop requested")

    def pause(self, state: LoopState) -> None:
        with self.lock:
            state.status = LoopStatus.PAUSED
            state.updated_at = time.monotonic()

    def resume(self, state: LoopState) -> bool:
        with self.lock:
            if state.status == LoopStatus.PAUSED:
                state.status = LoopStatus.RUNNING
                state.updated_at = time.monotonic()
                return True
            return False

    def check_limits(self, state: LoopState) -> bool:
        """Returns True if loop may continue, False if limits are exceeded."""
        with self.lock:
            now = time.monotonic()
            if state.iteration >= self.max_iterations:
                logger.warning("Iteration limit reached (%d)", self.max_iterations)
                return False
            if state.started_at > 0 and (now - state.started_at) > self.max_duration_sec:
                logger.warning("Duration limit reached (%.1fs)", self.max_duration_sec)
                return False
            if state.consecutive_failures >= self.max_consecutive_failures:
                logger.warning("Consecutive failure limit reached (%d)", self.max_consecutive_failures)
                return False
            return True

    def check_watchdog(self, state: LoopState) -> bool:
        """Returns True if phase execution is within timeout, False otherwise."""
        with self.lock:
            if self._phase_start_time > 0:
                elapsed = time.monotonic() - self._phase_start_time
                if elapsed > self.watchdog_timeout_sec:
                    logger.error("Watchdog timeout in phase %s (%.1fs)", state.phase.value, elapsed)
                    return False
            return True

    def mark_phase_start(self) -> None:
        self._phase_start_time = time.monotonic()

    def mark_phase_end(self, state: LoopState, phase_name: str) -> None:
        duration = time.monotonic() - self._phase_start_time
        state.phase_durations[phase_name] = state.phase_durations.get(phase_name, 0.0) + duration
        self._phase_start_time = 0.0

    def get_statistics(self, state: LoopState) -> Dict[str, Any]:
        with self.lock:
            return {
                "iteration": state.iteration,
                "status": state.status.value,
                "total_successes": state.total_successes,
                "total_failures": state.total_failures,
                "total_recoveries": state.total_recoveries,
                "consecutive_failures": state.consecutive_failures,
                "phase_durations": state.phase_durations,
                "runtime_sec": time.monotonic() - state.started_at if state.started_at else 0.0
            }
