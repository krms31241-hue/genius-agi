"""
Ollama Provider
Genius AGI

Local offline model provider.

Supports:
- Local Ollama server
- Streaming generation
- Model information
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator

import ollama


from .provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
    ProviderCapabilities,
    ProviderUsage,
    ProviderUnavailableError,
    ProviderError,
)


logger = logging.getLogger(__name__)


class OllamaProvider(ProviderBase):

    def __init__(
        self,
        config: ProviderConfig,
    ) -> None:

        super().__init__(config)


        self.host = config.extra.get(
            "host",
            "http://localhost:11434",
        )


        self.client = ollama.AsyncClient(
            host=self.host
        )


        self._capabilities = ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=True,
            supports_functions=False,
            max_context_tokens=32768,
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
        Generate response using local Ollama.
        """

        try:

            params = self._merge_kwargs(kwargs)


            response = await self.client.chat(
                model=self.config.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": self._prepare_prompt(prompt),
                    }
                ],
                options={
                    "temperature": params["temperature"],
                    "top_p": params["top_p"],
                    "num_predict": params["max_tokens"],
                },
            )


            content = (
                response
                .get("message", {})
                .get("content", "")
            )


            return ProviderResponse(
                content=content,
                model=self.config.model_name,
                raw=response,
            )


        except ConnectionError as exc:

            raise ProviderUnavailableError(
                "Ollama server unavailable",
                "ollama",
            ) from exc


        except Exception as exc:

            logger.exception(
                "Ollama generation failed"
            )

            raise ProviderError(
                str(exc),
                "ollama",
            ) from exc



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream Ollama response.
        """

        try:

            params = self._merge_kwargs(kwargs)


            stream = await self.client.chat(
                model=self.config.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": self._prepare_prompt(prompt),
                    }
                ],
                options={
                    "temperature": params["temperature"],
                    "top_p": params["top_p"],
                    "num_predict": params["max_tokens"],
                },
                stream=True,
            )


            async for chunk in stream:

                text = (
                    chunk
                    .get("message", {})
                    .get("content", "")
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
                "ollama",
            ) from exc




    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return Ollama model information.
        """

        try:

            models = await self.client.list()

            model_names = []


            if hasattr(models, "models"):

                model_names = [
                    item.model
                    for item in models.models
                ]

            elif isinstance(models, dict):

                model_names = [
                    item.get("name")
                    for item in models.get(
                        "models",
                        []
                    )
                ]


            self._capabilities.supported_models = (
                model_names
            )


            return {
                "provider": "ollama",
                "host": self.host,
                "model": self.config.model_name,
                "available_models": model_names,
                "capabilities": (
                    await self.get_capabilities()
                ).to_dict(),
            }


        except Exception as exc:

            raise ProviderError(
                str(exc),
                "ollama",
            ) from exc



    async def embed(
        self,
        text: str,
        **kwargs: Any,
    ) -> list[float]:
        """
        Generate local embeddings.
        """

        try:

            result = await self.client.embed(
                model=self.config.model_name,
                input=text,
            )

            return result.embeddings[0]


        except Exception as exc:

            raise ProviderError(
                str(exc),
                "ollama",
            ) from exc



    async def close(
        self,
    ) -> None:

        await super().close()



__all__ = [
    "OllamaProvider",
]


