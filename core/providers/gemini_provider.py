"""
Gemini Provider
Genius AGI

Direct REST implementation.
No google-genai dependency.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator

import httpx

from .provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
    ProviderUsage,
    ProviderCapabilities,
    AuthenticationError,
    RateLimitError,
    ProviderUnavailableError,
    ProviderTimeoutError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(ProviderBase):

    BASE_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models"
    )

    def __init__(
        self,
        config: ProviderConfig,
    ) -> None:

        super().__init__(config)

        keys = config.extra.get("api_keys")

        if isinstance(keys, list) and keys:
            self.api_keys = keys
        else:
            self.api_keys = [config.api_key]

        self.current_key = 0

        self.client = httpx.AsyncClient(
            timeout=config.timeout
        )

        self._capabilities = ProviderCapabilities(
            supports_streaming=True,
            supports_embeddings=False,
            supports_functions=False,
            max_context_tokens=1000000,
            max_completion_tokens=config.max_tokens,
            supported_models=[
                "gemini-2.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
            ],
        )


    def _key(self) -> str:
        return self.api_keys[self.current_key]


    def _rotate_key(self) -> None:

        if len(self.api_keys) > 1:
            self.current_key = (
                self.current_key + 1
            ) % len(self.api_keys)


    def _url(self, model_name: str | None = None) -> str:
        model = model_name or self.config.model_name

        if not model:
            raise ProviderError(
                "Gemini model was not selected by router"
            )

        return (
            f"{self.BASE_URL}/"
            f"{model}:generateContent"
            f"?key={self._key()}"
        )

    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate response using Gemini REST API.
        """

        attempts = len(self.api_keys)
        last_error = None

        model_name = (
            kwargs.pop("model", None)
            or self.config.model_name
        )

        if not model_name:
            raise ProviderError(
                "No Gemini model configured"
            )

        params = self._merge_kwargs(kwargs)

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": self._prepare_prompt(prompt)
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": params["temperature"],
                "topP": params["top_p"],
                "maxOutputTokens": params["max_tokens"],
            },
        }

        for _ in range(attempts):

            try:
                response = await self.client.post(
                    self._url(model_name),
                    json=payload,
                )


                if response.status_code == 401 or response.status_code == 403:
                    print("===== GEMINI AUTH DEBUG =====")
                    print("MODEL:", model_name)
                    print("KEY PREFIX:", self._key()[:8] if self._key() else "EMPTY")
                    print("=============================")
                    self._rotate_key()
                    raise AuthenticationError(
                    )

                if response.status_code == 429:
                    print("===== GEMINI QUOTA DEBUG =====")
                    print("==============================")
                    raise RateLimitError(
                        "Gemini quota exceeded"
                    )

                if response.status_code >= 500:
                    raise ProviderUnavailableError(
                        "Gemini service unavailable"
                    )

                response.raise_for_status()

                data = response.json()

                candidates = data.get(
                    "candidates",
                    []
                )

                if not candidates:
                    raise ProviderError(
                        "Gemini returned empty response"
                    )

                content = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )

                usage_data = data.get(
                    "usageMetadata",
                    {}
                )

                usage = ProviderUsage(
                    prompt_tokens=usage_data.get(
                        "promptTokenCount",
                        0,
                    ),
                    completion_tokens=usage_data.get(
                        "candidatesTokenCount",
                        0,
                    ),
                    total_tokens=usage_data.get(
                        "totalTokenCount",
                        0,
                    ),
                )

                return ProviderResponse(
                    content=content,
                    usage=usage,
                    model=model_name,
                    finish_reason=(
                        candidates[0]
                        .get("finishReason", "")
                    ),
                    raw=data,
                )


            except AuthenticationError:
                last_error = "Authentication failed"
                self._rotate_key()
                continue

            except RateLimitError as exc:
                last_error = str(exc)
                raise


            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(
                    str(exc)
                )


            except httpx.RequestError as exc:
                raise ProviderUnavailableError(
                    str(exc)
                )


            except Exception as exc:
                last_error = exc
                logger.exception(
                    "Gemini generation failed"
                )
                break


        raise ProviderError(
            f"All Gemini keys failed: {last_error}"
        )


    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        """
        Gemini streaming response.
        """

        params = self._merge_kwargs(kwargs)

        model_name = kwargs.get("model") or self.config.model_name

        url = (
            f"{self.BASE_URL}/"
            f"{model_name}:streamGenerateContent"
            f"?key={self._key()}"
            "&alt=sse"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": self._prepare_prompt(prompt)
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": params["temperature"],
                "topP": params["top_p"],
                "maxOutputTokens": params["max_tokens"],
            },
        }

        try:
            async with self.client.stream(
                "POST",
                url,
                json=payload,
            ) as response:

                response.raise_for_status()

                async for line in response.aiter_lines():

                    if not line.startswith("data:"):
                        continue

                    data = line.replace(
                        "data:",
                        "",
                    ).strip()

                    if not data:
                        continue

                    try:
                        chunk = __import__(
                            "json"
                        ).loads(data)

                        text = (
                            chunk
                            .get("candidates", [{}])[0]
                            .get("content", {})
                            .get("parts", [{}])[0]
                            .get("text", "")
                        )

                        if text:
                            yield ProviderResponse(
                                content=text,
                                model=self.config.model_name,
                                raw=chunk,
                            )

                    except Exception:
                        continue


        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(
                str(exc)
            )

        except httpx.RequestError as exc:
            raise ProviderUnavailableError(
                str(exc)
            )


    async def get_model_info(
        self,
    ) -> dict[str, Any]:

        return {
            "provider": "gemini",
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

        await super().validate_config()

        if not self.api_keys:
            raise AuthenticationError(
                "No Gemini API keys available"
            )


    async def close(
        self,
    ) -> None:

        if self.closed:
            return

        await self.client.aclose()

        await super().close()


__all__ = [
    "GeminiProvider",
]

