"""
Providers Bootstrap
Genius AGI

Initializes and registers AI providers.
"""

from __future__ import annotations

import logging
import os

from core.providers import (
    ProviderManager,
    ProviderConfig,
    OpenAIProvider,
    AnthropicProvider,
    OpenRouterProvider,
    GeminiProvider,
)

from core.config.providers_config import (
    ProvidersConfigManager,
)


logger = logging.getLogger(__name__)


class ProvidersBootstrap:
    """
    Builds provider runtime.
    """


    def __init__(self) -> None:

        self.config_manager = (
            ProvidersConfigManager()
        )

        self.manager = (
            ProviderManager()
        )


    def _config(
        self,
        model: str,
        key: str,
    ) -> ProviderConfig:

        return ProviderConfig(
            api_key=key,
            model_name=model,
            timeout=60,
        )


    async def initialize(
        self,
    ) -> ProviderManager:

        self.config_manager.load_from_env()

        await self._register_openrouter_only()

        logger.info(
            "Providers loaded: %s",
            self.manager.list_providers(),
        )

        return self.manager





    async def _register_openrouter_only(self):
        """Register only working providers."""
        
        openrouter_key = self.config_manager.get_key("openrouter")

        if openrouter_key:
            try:
                provider = OpenRouterProvider(
                    self._config(
                        os.getenv(
                            "OPENROUTER_MODEL",
                            "openrouter/auto"
                        ),
                        openrouter_key,
                    )
                )

                await self.manager.register(
                    "openrouter",
                    provider,
                    priority=1,
                )

            except Exception as exc:
                logger.warning(
                    "OpenRouter provider failed: %s",
                    exc,
                )


__all__ = [
    "ProvidersBootstrap",
]

