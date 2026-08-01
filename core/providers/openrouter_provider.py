"""
OpenRouter Provider
Genius AGI

Production implementation.

Supports:
- Multiple API keys
- Automatic key rotation
- OpenAI compatible API
- Streaming
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



class OpenRouterProvider(ProviderBase):

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
            supported_models=[],
        )


    def _create_client(self):

        return AsyncOpenAI(
            api_key=self.api_keys[self.current_key],
            base_url="https://openrouter.ai/api/v1",
            timeout=self.config.timeout,
            default_headers={
                "HTTP-Referer": "https://genius-agi.local",
                "X-Title": "Genius AGI",
            },
        )


    def _rotate_key(self):

        if len(self.api_keys) <= 1:
            return


        self.current_key = (
            self.current_key + 1
        ) % len(self.api_keys)


        self.client = self._create_client()


        logger.warning(
            "OpenRouter API key rotated"
        )




    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate response using OpenRouter.
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
                    "openrouter",
                ) from exc


            except asyncio.TimeoutError as exc:

                raise ProviderTimeoutError(
                    "OpenRouter timeout",
                    "openrouter",
                ) from exc


            except APIError as exc:

                raise ProviderError(
                    str(exc),
                    "openrouter",
                ) from exc


            except Exception as exc:

                last_error = exc

                logger.exception(
                    "OpenRouter generation failed"
                )

                break


        raise ProviderError(
            f"All OpenRouter keys failed: {last_error}",
            "openrouter",
        )



    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Stream OpenRouter response.
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
                "openrouter",
            ) from exc




    async def get_model_info(
        self,
    ) -> dict[str, Any]:
        """
        Return OpenRouter provider information.
        """

        return {
            "provider": "openrouter",
            "model": self.config.model_name,
            "capabilities": (
                await self.get_capabilities()
            ).to_dict(),
            "active_key_index": self.current_key,
            "total_keys": len(self.api_keys),
            "endpoint": "https://openrouter.ai/api/v1",
        }



    async def validate_config(
        self,
    ) -> None:
        """
        Validate OpenRouter configuration.
        """

        await super().validate_config()

        if not self.api_keys:
            raise AuthenticationError(
                "No OpenRouter API keys available",
                "openrouter",
            )



    async def close(
        self,
    ) -> None:
        """
        Close OpenRouter client.
        """

        if self.closed:
            return

        await self.client.close()

        await super().close()



__all__ = [
    "OpenRouterProvider",
]


