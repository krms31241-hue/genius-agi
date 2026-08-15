"""Initialize the configured AI provider with an offline fallback."""

import logging
import os
from typing import Any, List

from core.ai_gateway_provider import AIGatewayProvider

logger = logging.getLogger(__name__)


class AIProvider:
    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError

    async def shutdown(self) -> None:
        return None


class LocalProvider(AIProvider):
    """Explicit offline fallback; it does not claim model reasoning."""

    def __init__(self) -> None:
        super().__init__("local-fallback", "offline-template-v1")

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        return "AI Gateway is not configured. Set AI_GATEWAY_API_KEY to enable model-backed responses."


class ProvidersBootstrap:
    def __init__(self) -> None:
        self.providers: List[AIProvider | AIGatewayProvider] = []
        self.active_provider: AIProvider | AIGatewayProvider | None = None

    async def initialize(self) -> "ProvidersBootstrap":
        api_key = os.getenv("AI_GATEWAY_API_KEY")
        if api_key:
            provider = AIGatewayProvider(
                api_key=api_key,
                model=os.getenv("AI_GATEWAY_MODEL", "google/gemini-3.1-flash-lite"),
            )
            logger.info("Initialized AI Gateway provider for model %s", provider.model)
        else:
            provider = LocalProvider()
            logger.warning("AI_GATEWAY_API_KEY is missing; using offline fallback")

        self.providers = [provider]
        self.active_provider = provider
        return self

    async def shutdown(self) -> None:
        for provider in self.providers:
            await provider.shutdown()
