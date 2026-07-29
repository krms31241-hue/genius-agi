"""Autonomous Executive Loop: O-A-P-E-E-I continuous execution with safety, recovery, and statistics."""
import time
import logging
from typing import Dict, Any, Callable, Optional
from .loop_state import LoopState, LoopPhase, LoopStatus
from .loop_controller import LoopController

logger = logging.getLogger(__name__)

PhaseHandler = Callable[[LoopState, Dict[str, Any]], Dict[str, Any]]

class AutonomousLoop:
    """Deterministic autonomous loop orchestrating Observe→Analyze→Plan→Execute→Evaluate→Improve."""
    def __init__(self, controller: LoopController, **kwargs):
        self.controller = controller
        self.phases: Dict[LoopPhase, PhaseHandler] = {}
        
        # Flexible initialization: supports both LoopPhase enum keys and named arguments (e.g., observe_fn)
        for phase in LoopPhase:
            fn = kwargs.get(phase) or kwargs.get(f"{phase.value}_fn")
            if fn:
                self.phases[phase] = fn
                
        self.recovery_fn = kwargs.get("recovery_fn", self._default_recovery)
        self.state = LoopState()
        self._phase_order = list(LoopPhase)

    def run(self, context: Optional[Dict[str, Any]] = None) -> LoopState:
        """Execute continuous loop until limits, stop request, or fatal failure."""
        if context:
            self.state.context.update(context)
        self.controller.start(self.state)
        logger.info("Autonomous loop started")

        while self.state.status == LoopStatus.RUNNING and not self.state.stop_requested:
            if not self.controller.check_limits(self.state):
                self.state.status = LoopStatus.COMPLETED
                break

            iteration_success = True

            for phase in self._phase_order:
                if self.state.stop_requested:
                    break
                self.state.phase = phase
                self.controller.mark_phase_start()

                try:
                    handler = self.phases.get(phase)
                    if not handler:
                        logger.warning("No handler for phase %s, skipping", phase.value)
                        self.controller.mark_phase_end(self.state, phase.value)
                        continue
                        
                    result = handler(self.state, self.state.context)
                    self.state.context.update(result or {})
                    
                    if not self.controller.check_watchdog(self.state):
                        raise TimeoutError(f"Watchdog timeout in {phase.value}")
                    
                    self.controller.mark_phase_end(self.state, phase.value)
                except Exception as e:
                    logger.error("Phase %s failed: %s", phase.value, e)
                    self.state.errors.append(f"{phase.value}: {str(e)}")
                    self.state.total_failures += 1
                    self.state.consecutive_failures += 1
                    iteration_success = False
                    self.controller.mark_phase_end(self.state, phase.value)

                    try:
                        self.recovery_fn(self.state, self.state.context)
                        self.state.total_recoveries += 1
                    except Exception as rec_err:
                        logger.error("Recovery failed: %s", rec_err)
                    break

            # Count iteration only if the cycle wasn't aborted by a stop request.
            # This ensures partial/aborted cycles don't inflate the iteration count,
            # satisfying safe-stop semantics while preserving limit checks.
            if not self.state.stop_requested:
                self.state.iteration += 1

            if iteration_success:
                self.state.total_successes += 1
                self.state.consecutive_failures = 0

            self.state.updated_at = time.monotonic()

        if self.state.stop_requested:
            self.state.status = LoopStatus.STOPPED
        elif self.state.consecutive_failures >= self.controller.max_consecutive_failures:
            self.state.status = LoopStatus.FAILED

        logger.info("Autonomous loop finished: %s after %d iterations", self.state.status.value, self.state.iteration)
        return self.state

    def request_stop(self) -> None:
        self.controller.stop(self.state)

    def get_statistics(self) -> Dict[str, Any]:
        return self.controller.get_statistics(self.state)

    def _default_recovery(self, state: LoopState, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("Default recovery triggered at iteration %d", state.iteration)
        context["recovered"] = True
        return {"recovery_status": "completed"}
