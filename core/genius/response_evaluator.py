import re
import logging
from typing import Optional

from core.genius.models import EvaluationResult

logger = logging.getLogger(__name__)


class ResponseEvaluator:
    _HALLUCINATION_PHRASES = [
        "i don't know",
        "i'm not sure",
        "i cannot",
        "i can't",
        "i am not able",
        "i don't have",
        "not available",
        "error",
    ]
    _INCOMPLETE_PHRASES = ["...", "…", "to be continued", "incomplete", "truncated"]

    def evaluate(self, response: str, context: Optional[str] = None) -> EvaluationResult:
        score = 1.0
        feedback = []
        requires_regeneration = False
        regeneration_reason = ""

        if len(response.strip()) < 10:
            score -= 0.3
            feedback.append("Response too short")
            requires_regeneration = True
            regeneration_reason = "Response too short"

        lower_res = response.lower()
        for phrase in self._HALLUCINATION_PHRASES:
            if phrase in lower_res:
                score -= 0.2
                feedback.append(f"Contains '{phrase}'")

        for phrase in self._INCOMPLETE_PHRASES:
            if phrase in lower_res:
                score -= 0.2
                feedback.append("Response appears incomplete")
                requires_regeneration = True
                regeneration_reason = "Response truncated or incomplete"

        if context and context.lower() not in lower_res:
            score -= 0.1
            feedback.append("Response may be off-topic")

        score = max(0.0, min(1.0, score))
        passed = score >= 0.6 and not requires_regeneration

        return EvaluationResult(
            passed=passed,
            score=score,
            feedback="; ".join(feedback) if feedback else "OK",
            requires_regeneration=requires_regeneration,
            regeneration_reason=regeneration_reason,
        )
