"""
vLLM Provider
Genius AGI

Provider for self-hosted vLLM OpenAI-compatible servers.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI


from .provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
    ProviderUsage,
    ProviderCapabilities,
    ProviderError,
    ProviderUnavailableError,
)


logger = logging.getLogger(__name__)


class VLLMProvider(ProviderBase):

    def __init__(
        self,
        config: ProviderConfig,
    ) -> None:

        super().__init__(config)


        self.base_url = config.extra.get(
            "base_url",
            "http://localhost:8000/v1",
        )


        self.client = AsyncOpenAI(
            api_key=(
                config.api_key
                or "EMPTY"
            ),
            base_url=self.base_url,
            timeout=config.timeout,
        )


        self._capabilities = ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=True,
            supports_functions=True,
            max_context_tokens=131072,
            max_completion_tokens=config.max_tokens,
            supported_models=[],
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
        Generate response through vLLM server.
        """

        try:

            params = self._merge_kwargs(kwargs)


            response = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": self._prepare_prompt(prompt),
                    }
                ],
                temperature=params["temperature"],
                top_p=params["top_p"],
                max_tokens=params["max_tokens"],
            )


            choice = response.choices[0]


            usage = ProviderUsage(
                prompt_tokens=(
                    response.usage.prompt_tokens
                    if response.usage
                    else 0
                ),
                completion_tokens=(
                    response.usage.completion_tokens
                    if response.usage
                    else 0
                ),
                total_tokens=(
                    response.usage.total_tokens
                    if response.usage
                    else 0
                ),
            )


            return ProviderResponse(
                content=choice.message.content or "",
                usage=usage,
                model=response.model,
                finish_reason=(
                    choice.finish_reason
                    or ""
                ),
                raw=response,
            )


        except Exception as exc:

            logger.exception(
                "vLLM generation failed"
            )

            raise ProviderError(
                str(exc),
                "vllm",
            ) from exc



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream response from vLLM.
        """

        try:

            params = self._merge_kwargs(kwargs)


            stream = await self.client.chat.completions.create(
                model=self.config.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": self._prepare_prompt(prompt),
                    }
                ],
                temperature=params["temperature"],
                max_tokens=params["max_tokens"],
                stream=True,
            )


            async for chunk in stream:

                if not chunk.choices:
                    continue


                text = (
                    chunk.choices[0]
                    .delta
                    .content
                )


                if text:

                    yield ProviderResponse(
                        content=text,
                        model=self.config.model_name,
                        raw=chunk,
                    )


        except Exception as exc:

            raise ProviderError(
                str(exc),
                "vllm",
            ) from exc




    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return vLLM model information.
        """

        try:

            models = await self.client.models.list()

            available = [
                model.id
                for model in models.data
            ]


            self._capabilities.supported_models = (
                available
            )


            return {
                "provider": "vllm",
                "endpoint": self.base_url,
                "model": self.config.model_name,
                "available_models": available,
                "capabilities": (
                    await self.get_capabilities()
                ).to_dict(),
            }


        except Exception as exc:

            raise ProviderUnavailableError(
                str(exc),
                "vllm",
            ) from exc



    async def validate_config(
        self,
    ) -> None:

        await super().validate_config()



    async def close(
        self,
    ) -> None:

        if self.closed:
            return

        await self.client.close()

        await super().close()



__all__ = [
    "VLLMProvider",
]


