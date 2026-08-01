"""
AI Router
==========

Routes every request through:

Prompt
   ↓
TaskAnalyzer
   ↓
TaskType
   ↓
ModelRegistry
   ↓
ProviderManager
   ↓
Best Provider
"""

from __future__ import annotations

import logging
from typing import Any

from core.router.task_analyzer import TaskAnalyzer
from core.router.model_registry import (
    registry,
    TaskType,
)

from core.providers.provider_manager import (
    ProviderManager,
)
from decision.decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class AIRouter:

    def __init__(
        self,
        provider_manager: ProviderManager,
    ) -> None:

        self.provider_manager = provider_manager
        self.task_analyzer = TaskAnalyzer()
        self.registry = registry
        self.decision_engine = DecisionEngine()



    def _build_decision_context(self, prompt: str, task):
        """
        Build read-only context for DecisionEngine.
        """
        candidates = self.registry.best_for(task)

        return {
            "prompt": prompt,
            "task": task.value,
            "available_models": [
                {
                    "name": m.name,
                    "provider": m.provider.value,
                    "reasoning": m.reasoning_score,
                    "coding": m.coding_score,
                    "vision": m.vision_score,
                    "speed": m.speed_score,
                    "cost": m.cost_score,
                }
                for m in candidates
            ],
        }


    def choose_model(
        self,
        prompt: str,
    ):

        task = self.task_analyzer.analyze(prompt)

        context = self._build_decision_context(prompt, task)

        decision = self.decision_engine.evaluate(
            goal=f"select_best_model_for_{task.value}",
            context=context,
        )

        candidates = self.registry.best_for(task)

        if not candidates:
            raise RuntimeError(
                f"No model available for task: {task}"
            )

        model = candidates[0]

        if decision.metadata:
            logger.info(
                "DecisionEngine selected strategy (score=%.2f confidence=%.2f)",
                decision.score,
                decision.confidence,
            )

        logger.info(
            "Task=%s -> Model=%s (%s)",
            task.value,
            model.name,
            model.provider.value,
        )

        return task, model


    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ):

        task, model = self.choose_model(prompt)

        response = await self.provider_manager.generate(
            prompt,
            provider=model.provider.value,
            model=model.name,
            task_type=task.value,
            **kwargs,
        )

        return response


    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ):

        task, model = self.choose_model(prompt)

        async for chunk in self.provider_manager.generate_stream(
            prompt,
            provider=model.provider.value,
            model=model.name,
            task_type=task.value,
            **kwargs,
        ):
            yield chunk



__all__ = [
    "AIRouter",
]
