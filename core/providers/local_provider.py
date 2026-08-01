"""
Local Provider
Genius AGI

Generic local model provider.

Designed for:
- Local inference engines
- Embedded models
- Custom runtimes
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Awaitable


from .provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
    ProviderCapabilities,
    ProviderError,
)


logger = logging.getLogger(__name__)



class LocalProvider(ProviderBase):

    def __init__(
        self,
        config: ProviderConfig,
        engine: Callable[..., Awaitable[str]] | None = None,
    ) -> None:

        super().__init__(config)

        self.engine = engine


        self._capabilities = ProviderCapabilities(
            supports_streaming=False,
            supports_embeddings=False,
            supports_functions=False,
            max_context_tokens=32768,
            max_completion_tokens=config.max_tokens,
            supported_models=[
                config.model_name
            ],
        )



    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        ...


    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate using local engine.
        """

        if self.engine is None:

            raise ProviderError(
                "No local inference engine configured",
                "local",
            )


        try:

            result = await self.engine(
                self._prepare_prompt(prompt),
                **kwargs,
            )


            return ProviderResponse(
                content=result,
                model=self.config.model_name,
            )


        except Exception as exc:

            logger.exception(
                "Local generation failed"
            )

            raise ProviderError(
                str(exc),
                "local",
            ) from exc



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream local generation.

        Default implementation splits generated output.
        """

        response = await self.generate(
            prompt,
            **kwargs,
        )


        for token in response.content.split():

            yield ProviderResponse(
                content=token + " ",
                model=self.config.model_name,
            )



    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return local model information.
        """

        return {
            "provider": "local",
            "model": self.config.model_name,
            "engine": (
                self.engine.__name__
                if self.engine
                else None
            ),
            "capabilities": (
                await self.get_capabilities()
            ).to_dict(),
        }




    async def validate_config(
        self,
    ) -> None:
        """
        Validate local provider.
        """

        await super().validate_config()


        if self.engine is None:

            logger.warning(
                "Local provider has no engine yet"
            )



    async def close(
        self,
    ) -> None:

        await super().close()



__all__ = [
    "LocalProvider",
]


