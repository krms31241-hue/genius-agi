"""
Provider Manager
Genius AGI

Central AI provider orchestration layer.

Features:
- Provider registration
- Priority routing
- Automatic fallback
- Health tracking
- Model capability routing
- Safe shutdown
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any


from .provider_base import (
    ProviderBase,
    ProviderResponse,
    ProviderError,
)


logger = logging.getLogger(__name__)


@dataclass
class ProviderStatus:
    """
    Runtime provider status.
    """

    name: str

    healthy: bool = True

    failures: int = 0

    successes: int = 0

    metadata: dict[str, Any] = field(
        default_factory=dict
    )


class ProviderManager:
    """
    Main provider orchestrator.
    """

    def __init__(self) -> None:

        self.providers: dict[str, ProviderBase] = {}

        self.priority: list[str] = []

        self.status: dict[str, ProviderStatus] = {}

        self.lock = asyncio.Lock()


    async def register(
        self,
        name: str,
        provider: ProviderBase,
        priority: int = 100,
    ) -> None:
        """
        Register provider.
        """

        async with self.lock:

            self.providers[name] = provider

            self.status[name] = ProviderStatus(
                name=name,
            )

            self.priority.append(name)

            self.priority.sort(
                key=lambda item: priority
            )


    def get(
        self,
        name: str,
    ) -> ProviderBase:
        """
        Get provider by name.
        """

        return self.providers[name]




    async def unregister(
        self,
        name: str,
    ) -> None:
        """
        Remove provider safely.
        """

        async with self.lock:

            provider = self.providers.get(name)

            if provider:

                await provider.close()

                del self.providers[name]


            self.status.pop(
                name,
                None,
            )


            self.priority = [
                item
                for item in self.priority
                if item != name
            ]



    async def shutdown(
        self,
    ) -> None:
        """
        Close all providers.
        """

        for provider in list(
            self.providers.values()
        ):

            try:

                await provider.close()

            except Exception:

                logger.exception(
                    "Provider shutdown failed"
                )



    async def generate(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        **kwargs: Any,
    ) -> ProviderResponse:
        """
        Generate with automatic fallback.
        """

        if provider:

            return await self.providers[
                provider
            ].generate(
                prompt,
                **kwargs,
            )


        last_error = None


        for name in self.priority:

            status = self.status.get(name)


            if status and not status.healthy:

                continue


            try:

                result = await self.providers[
                    name
                ].generate(
                    prompt,
                    **kwargs,
                )


                if status:

                    status.successes += 1

                    status.healthy = True


                return result


            except Exception as exc:

                last_error = exc


                if status:

                    status.failures += 1

                    status.healthy = False


                logger.warning(
                    "Provider %s failed: %s",
                    name,
                    exc,
                )


        raise ProviderError(
            f"All providers failed: {last_error}"
        )




    async def generate_stream(
        self,
        prompt: str,
        *,
        provider: str | None = None,
        **kwargs: Any,
    ):
        """
        Streaming generation with fallback.
        """

        if provider:

            async for chunk in self.providers[
                provider
            ].generate_stream(
                prompt,
                **kwargs,
            ):

                yield chunk

            return



        last_error = None


        for name in self.priority:

            status = self.status.get(name)


            if status and not status.healthy:

                continue


            try:

                async for chunk in self.providers[
                    name
                ].generate_stream(
                    prompt,
                    **kwargs,
                ):

                    yield chunk


                if status:

                    status.successes += 1

                    status.healthy = True


                return


            except Exception as exc:

                last_error = exc


                if status:

                    status.failures += 1

                    status.healthy = False


                logger.warning(
                    "Streaming provider %s failed: %s",
                    name,
                    exc,
                )


        raise ProviderError(
            f"All streaming providers failed: {last_error}"
        )



    async def health(
        self,
    ) -> dict[str, bool]:
        """
        Check providers health.
        """

        result: dict[str, bool] = {}


        for name, provider in self.providers.items():

            try:

                await provider.get_model_info()


                result[name] = True


                if name in self.status:

                    self.status[name].healthy = True


            except Exception:

                result[name] = False


                if name in self.status:

                    self.status[name].healthy = False


        return result



    def provider_count(
        self,
    ) -> int:
        """
        Return number of providers.
        """

        return len(
            self.providers
        )



    def list_providers(
        self,
    ) -> list[str]:
        """
        Return providers names.
        """

        return list(
            self.providers.keys()
        )



__all__ = [
    "ProviderManager",
    "ProviderStatus",
]

