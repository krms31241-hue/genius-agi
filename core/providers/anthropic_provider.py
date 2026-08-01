"""
Anthropic Provider
Genius AGI

Production provider implementation.
Supports:
- Multiple API keys
- Key rotation
- Streaming
- Error handling
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import anthropic


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


class AnthropicProvider(ProviderBase):

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
            supports_embeddings=False,
            supports_functions=True,
            max_context_tokens=200000,
            max_completion_tokens=config.max_tokens,
            supported_models=[
                "claude-3-5-sonnet",
                "claude-3-5-haiku",
                "claude-3-opus",
            ],
        )


    def _create_client(self):
        return anthropic.AsyncAnthropic(
            api_key=self.api_keys[self.current_key],
            timeout=self.config.timeout,
        )


    def _rotate_key(self):

        if len(self.api_keys) <= 1:
            return

        self.current_key = (
            self.current_key + 1
        ) % len(self.api_keys)

        self.client = self._create_client()

        logger.warning(
            "Anthropic API key rotated"
        )


    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate response using Anthropic.
        """

        attempts = len(self.api_keys)

        last_error = None

        for _ in range(attempts):

            try:

                params = self._merge_kwargs(kwargs)


                response = await self.client.messages.create(
                    model=self.config.model_name,
                    max_tokens=params["max_tokens"],
                    temperature=params["temperature"],
                    top_p=params["top_p"],
                    messages=[
                        {
                            "role": "user",
                            "content": self._prepare_prompt(prompt),
                        }
                    ],
                )


                content = ""

                if response.content:
                    content = response.content[0].text


                usage = ProviderUsage(
                    prompt_tokens=(
                        response.usage.input_tokens
                        if response.usage
                        else 0
                    ),
                    completion_tokens=(
                        response.usage.output_tokens
                        if response.usage
                        else 0
                    ),
                    total_tokens=(
                        (
                            response.usage.input_tokens
                            +
                            response.usage.output_tokens
                        )
                        if response.usage
                        else 0
                    ),
                )


                return ProviderResponse(
                    content=content,
                    usage=usage,
                    model=response.model,
                    finish_reason=(
                        response.stop_reason
                        or ""
                    ),
                    raw=response,
                )


            except anthropic.AuthenticationError as exc:

                last_error = exc

                self._rotate_key()

                continue


            except anthropic.RateLimitError as exc:

                last_error = exc

                self._rotate_key()

                continue


            except anthropic.APIConnectionError as exc:

                raise ProviderUnavailableError(
                    str(exc),
                    "anthropic",
                ) from exc


            except asyncio.TimeoutError as exc:

                raise ProviderTimeoutError(
                    "Anthropic timeout",
                    "anthropic",
                ) from exc


            except Exception as exc:

                last_error = exc

                logger.exception(
                    "Anthropic generation failed"
                )

                break


        raise ProviderError(
            f"All Anthropic keys failed: {last_error}",
            "anthropic",
        )



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Streaming generation.
        """

        try:

            params = self._merge_kwargs(kwargs)


            async with self.client.messages.stream(
                model=self.config.model_name,
                max_tokens=params["max_tokens"],
                temperature=params["temperature"],
                messages=[
                    {
                        "role": "user",
                        "content": self._prepare_prompt(prompt),
                    }
                ],
            ) as stream:


                async for text in stream.text_stream:

                    yield ProviderResponse(
                        content=text,
                        model=self.config.model_name,
                    )


        except Exception as exc:

            logger.exception(
                "Anthropic streaming failed"
            )

            raise ProviderError(
                str(exc),
                "anthropic",
            ) from exc




    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return provider information.
        """

        return {
            "provider": "anthropic",
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
        Validate configuration.
        """

        await super().validate_config()

        if not self.api_keys:
            raise AuthenticationError(
                "No Anthropic API keys available",
                "anthropic",
            )



    async def close(
        self,
    ) -> None:
        """
        Close Anthropic client.
        """

        if self.closed:
            return

        await self.client.close()

        await super().close()



__all__ = [
    "AnthropicProvider",
]


