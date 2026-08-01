"""
Provider Base
Core abstraction for every Genius provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, AsyncIterator


# ==========================================================
# Exceptions
# ==========================================================

class ProviderError(Exception):
    pass


class AuthenticationError(ProviderError):
    pass


class RateLimitError(ProviderError):
    pass


class ConfigurationError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderNotImplementedError(ProviderError):
    pass


# ==========================================================
# Config
# ==========================================================

@dataclass(slots=True)
class ProviderConfig:
    api_key: str
    model_name: str

    timeout: float = 60.0

    temperature: float = 0.7

    top_p: float = 1.0

    max_tokens: int = 4096

    stop: list[str] | None = None

    extra: dict[str, Any] = field(default_factory=dict)

# ==========================================================
# Usage
# ==========================================================

@dataclass(slots=True)
class ProviderUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    extra: dict[str, Any] = field(default_factory=dict)


# ==========================================================
# Response
# ==========================================================

@dataclass(slots=True)
class ProviderResponse:
    content: str

    usage: ProviderUsage = field(default_factory=ProviderUsage)

    model: str = ""

    finish_reason: str = ""

    raw: Any = None

    extra: dict[str, Any] = field(default_factory=dict)


# ==========================================================
# Capabilities
# ==========================================================

@dataclass(slots=True)
class ProviderCapabilities:
    supports_streaming: bool = False
    supports_embeddings: bool = False
    supports_functions: bool = False

    max_context_tokens: int = 0
    max_completion_tokens: int = 0
    supported_models: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

# ==========================================================
# Abstract Provider
# ==========================================================

class ProviderBase(ABC):

    def __init__(self, config: ProviderConfig):
        self.config = config
        self._closed = False
        self._capabilities = ProviderCapabilities()

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> ProviderResponse:
        ...

    async def generate_stream(
        self,
        prompt: str,
        **kwargs: Any,
    ) -> AsyncIterator[ProviderResponse]:
        raise ProviderNotImplementedError(
            "Streaming is not supported."
        )

    @abstractmethod
    async def get_model_info(self) -> dict[str, Any]:
        ...

    async def embed(
        self,
        text: str,
        **kwargs: Any,
    ) -> list[float]:
        raise ProviderNotImplementedError(
            "Embeddings are not supported."
        )

    async def count_tokens(
        self,
        text: str,
        model: str | None = None,
    ) -> int:
        return len(text.split())

    async def validate_config(self) -> None:
        if not self.config.api_key:
            raise ConfigurationError("Missing api_key")

        if not self.config.model_name:
            raise ConfigurationError("Missing model_name")

    def _prepare_prompt(self, prompt: str) -> str:
        return prompt

    def _merge_kwargs(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        return {
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stop": kwargs.get("stop", self.config.stop),
        }

    async def get_capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    async def close(self) -> None:
        self._closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    @property
    def closed(self) -> bool:
        return self._closed

