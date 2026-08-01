"""
Genius Provider
Genius AGI

Internal AI orchestration provider.

Responsible for:
- Internal routing
- Agent communication
- Custom Genius models
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



class GeniusProvider(ProviderBase):

    def __init__(
        self,
        config: ProviderConfig,
        executor: Callable[..., Awaitable[str]] | None = None,
    ) -> None:

        super().__init__(config)

        self.executor = executor


        self._capabilities = ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=False,
            supports_functions=True,
            max_context_tokens=100000,
            max_completion_tokens=config.max_tokens,
            supported_models=[
                "genius-core"
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
        Execute internal Genius pipeline.
        """

        if self.executor is None:

            raise ProviderError(
                "No Genius executor configured",
                "genius",
            )


        try:

            result = await self.executor(
                self._prepare_prompt(prompt),
                **kwargs,
            )


            return ProviderResponse(
                content=result,
                model="genius-core",
                extra={
                    "internal": True,
                },
            )


        except Exception as exc:

            logger.exception(
                "Genius execution failed"
            )

            raise ProviderError(
                str(exc),
                "genius",
            ) from exc



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream internal Genius execution.
        """

        response = await self.generate(
            prompt,
            **kwargs,
        )


        yield ProviderResponse(
            content=response.content,
            model="genius-core",
            extra={
                "internal": True,
            },
        )



    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return Genius internal information.
        """

        return {
            "provider": "genius",
            "model": "genius-core",
            "internal": True,
            "capabilities": (
                await self.get_capabilities()
            ).to_dict(),
        }




    async def validate_config(
        self,
    ) -> None:
        """
        Validate Genius provider.
        """

        await super().validate_config()


        if self.executor is None:

            logger.warning(
                "Genius provider has no executor configured yet"
            )



    async def close(
        self,
    ) -> None:

        await super().close()



__all__ = [
    "GeniusProvider",
]


