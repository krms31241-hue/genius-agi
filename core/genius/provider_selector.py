import logging
from typing import Dict, List, Optional, Tuple

from core.genius.exceptions import ProviderSelectionError
from core.genius.models import ClassificationResult, ProviderSelection
from core.providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class ProviderSelector:
    def __init__(self, provider_manager: ProviderManager) -> None:
        self.provider_manager = provider_manager

    def select(self, classification: ClassificationResult, context: Optional[Dict] = None) -> ProviderSelection:
        # Get available providers
        try:
            providers = self.provider_manager.get_available_providers()
        except AttributeError:
            providers = getattr(self.provider_manager, "providers", [])
            if not providers:
                raise ProviderSelectionError("No providers available")

        scored: List[Tuple[float, str, str]] = []
        for provider in providers:
            name = getattr(provider, "name", "unknown")
            model = getattr(provider, "model", "default")
            capabilities = getattr(provider, "capabilities", {})
            cost = capabilities.get("cost", 1.0)
            latency = capabilities.get("latency", 1.0)
            priority = capabilities.get("priority", 0)
            score = (1.0 / (cost + 0.1)) + (1.0 / (latency + 0.1)) + (priority * 0.5)
            supported_tasks = capabilities.get("supported_tasks", [])
            if classification.task_type.value in supported_tasks:
                score += 2.0
            scored.append((score, name, model))

        if not scored:
            raise ProviderSelectionError("No providers could be scored")

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_name, best_model = scored[0]

        return ProviderSelection(
            provider_name=best_name,
            model_name=best_model,
            priority=0,
            estimated_cost=0.0,
            estimated_latency=0.0,
            reasoning=f"Selected {best_name} with score {best_score:.2f}",
        )
