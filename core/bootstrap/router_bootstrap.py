"""
Router Bootstrap
Safe bootstrap for Genius AGI routing.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.router.ai_router import AIRouter
from core.providers.provider_manager import ProviderManager


@dataclass(slots=True)
class RouterRuntime:
    router: AIRouter
    provider_manager: ProviderManager


class RouterBootstrap:

    def __init__(self, provider_manager: ProviderManager):
        self.provider_manager = provider_manager

    def build(self) -> RouterRuntime:
        router = AIRouter(self.provider_manager)

        return RouterRuntime(
            router=router,
            provider_manager=self.provider_manager,
        )
