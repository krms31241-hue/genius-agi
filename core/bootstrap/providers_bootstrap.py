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

        await self._register_online()

        logger.info(
            "Providers loaded: %s",
            self.manager.list_providers(),
        )

        return self.manager




    async def _register_online(
        self,
    ) -> None:
        """
        Register available online providers.
        """


        openai_key = self.config_manager.get_key(
            "openai"
        )

        if openai_key:

            try:

                provider = OpenAIProvider(
                    self._config(
                        os.getenv(
                            "OPENAI_MODEL",
                            "gpt-4.1-mini",
                        ),
                        openai_key,
                    )
                )


                await self.manager.register(
                    "openai",
                    provider,
                    priority=10,
                )


            except Exception as exc:

                logger.warning(
                    "OpenAI provider failed: %s",
                    exc,
                )



        anthropic_key = self.config_manager.get_key(
            "anthropic"
        )

        if anthropic_key:

            try:

                provider = AnthropicProvider(
                    self._config(
                        os.getenv(
                            "ANTHROPIC_MODEL",
                            "claude-3-5-sonnet",
                        ),
                        anthropic_key,
                    )
                )


                await self.manager.register(
                    "anthropic",
                    provider,
                    priority=20,
                )


            except Exception as exc:

                logger.warning(
                    "Anthropic provider failed: %s",
                    exc,
                )





        gemini_key = self.config_manager.get_key(
            "gemini"
        )

        if gemini_key:
            try:
                provider = GeminiProvider(
                    self._config(
                        os.getenv(
                            "GEMINI_MODEL",
                            "gemini-2.5-flash",
                        ),
                        gemini_key,
                    )
                )

                await self.manager.register(
                    "gemini",
                    provider,
                    priority=15,
                )

            except Exception as exc:
                logger.warning(
                    "Gemini provider failed: %s",
                    exc,
                )

        openrouter_key = self.config_manager.get_key(
            "openrouter"
        )


        if openrouter_key:

            try:

                provider = OpenRouterProvider(
                    self._config(
                        os.getenv(
                            "OPENROUTER_MODEL",
                            "openrouter/auto",
                        ),
                        openrouter_key,
                    )
                )


                await self.manager.register(
                    "openrouter",
                    provider,
                    priority=30,
                )


            except Exception as exc:

                logger.warning(
                    "OpenRouter provider failed: %s",
                    exc,
                )



__all__ = [
    "ProvidersBootstrap",
]

