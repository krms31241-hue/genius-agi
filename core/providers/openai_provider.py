"""
OpenAI Provider
Genius AGI

Production provider implementation.
Supports:
- Multiple API keys
- Automatic key rotation
- Retry handling
- Streaming
- Async execution
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

from openai import AsyncOpenAI
from openai import APIError
from openai import APIConnectionError
from openai import AuthenticationError as OpenAIAuthError
from openai import RateLimitError as OpenAIRateLimitError


from .provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
    ProviderUsage,
    ProviderCapabilities,
    AuthenticationError,
    RateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderError,
)


logger = logging.getLogger(__name__)


class OpenAIProvider(ProviderBase):
    """
    OpenAI API provider.

    The provider is responsible only for communication
    with OpenAI models.

    Model routing is handled by ProviderManager.
    """

    def __init__(
        self,
        config: ProviderConfig,
    ) -> None:

        super().__init__(config)

        keys = config.extra.get("api_keys")

        if keys and isinstance(keys, list):
            self.api_keys = keys
        else:
            self.api_keys = [
                config.api_key
            ]

        self.current_key = 0

        self.client = self._create_client()

        self._capabilities = ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=True,
            supports_functions=True,
            max_context_tokens=200000,
            max_completion_tokens=config.max_tokens,
            supported_models=[
                "gpt-5",
                "gpt-5-mini",
                "gpt-4.1",
                "gpt-4o",
                "gpt-4o-mini",
                "o3",
                "o4-mini",
            ],
        )


    def _create_client(self) -> AsyncOpenAI:
        """
        Create OpenAI async client.
        """

        return AsyncOpenAI(
            api_key=self.api_keys[self.current_key],
            timeout=self.config.timeout,
        )


    def _rotate_key(self) -> None:
        """
        Switch to next API key.
        """

        if len(self.api_keys) <= 1:
            return

        self.current_key = (
            self.current_key + 1
        ) % len(self.api_keys)

        self.client = self._create_client()

        logger.warning(
            "OpenAI API key rotated"
        )


    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate response from OpenAI.
        """

        attempts = len(self.api_keys)

        last_error = None

        for _ in range(attempts):

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
                    stop=params["stop"],
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
                        choice.finish_reason or ""
                    ),
                    raw=response,
                )


            except OpenAIAuthError as exc:

                last_error = exc

                self._rotate_key()

                continue


            except OpenAIRateLimitError as exc:

                last_error = exc

                self._rotate_key()

                continue


            except APIConnectionError as exc:

                raise ProviderUnavailableError(
                    str(exc),
                    "openai",
                ) from exc


            except asyncio.TimeoutError as exc:

                raise ProviderTimeoutError(
                    "OpenAI request timeout",
                    "openai",
                ) from exc


            except APIError as exc:

                raise ProviderError(
                    str(exc),
                    "openai",
                ) from exc


            except Exception as exc:

                last_error = exc

                logger.exception(
                    "Unexpected OpenAI error"
                )

                break


        raise ProviderError(
            f"All OpenAI keys failed: {last_error}",
            "openai",
        )


    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream OpenAI responses.
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
                top_p=params["top_p"],
                max_tokens=params["max_tokens"],
                stream=True,
            )


            async for chunk in stream:

                if not chunk.choices:
                    continue

                delta = (
                    chunk.choices[0]
                    .delta
                    .content
                )

                if delta:

                    yield ProviderResponse(
                        content=delta,
                        model=self.config.model_name,
                        raw=chunk,
                    )


        except Exception as exc:

            logger.exception(
                "OpenAI streaming failed"
            )

            raise ProviderError(
                str(exc),
                "openai",
            ) from exc



    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return model information.
        """

        return {
            "provider": "openai",
            "model": self.config.model_name,
            "available_models": (
                self._capabilities.supported_models
            ),
            "capabilities": (
                await self.get_capabilities()
            ).to_dict(),
            "active_key_index": self.current_key,
            "total_keys": len(self.api_keys),
        }


    async def validate_config(
        self,
    ) -> None:
        """
        Validate OpenAI configuration.
        """

        await super().validate_config()

        if not self.api_keys:
            raise AuthenticationError(
                "No OpenAI API keys available",
                "openai",
            )


    async def close(
        self,
    ) -> None:
        """
        Close OpenAI client.
        """

        if self.closed:
            return

        await self.client.close()

        await super().close()



__all__ = [
    "OpenAIProvider",
]

