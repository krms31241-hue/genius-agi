"""
Genius AGI Runtime
Connects:
Providers -> Router -> Memory -> Executive
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.bootstrap.providers_bootstrap import ProvidersBootstrap
from core.router.ai_router import AIRouter
from memory.memory_manager import MemoryManager


logger = logging.getLogger(__name__)


class GeniusRuntime:

    def __init__(self):
        self.providers = None
        self.router = None
        self.memory = MemoryManager()

    async def initialize(self):

        bootstrap = ProvidersBootstrap()

        self.providers = await bootstrap.initialize()

        self.router = AIRouter(
            self.providers
        )

        logger.info(
            "Genius Runtime initialized"
        )


    async def run(
        self,
        prompt: str,
        **kwargs: Any
    ) -> Dict[str, Any]:

        if not self.router:
            raise RuntimeError(
                "Runtime not initialized"
            )

        # Retrieve memory context
        memories = []

        try:
            memories = self.memory.search_facts(
                prompt
            )
        except Exception:
            pass


        response = await self.router.generate(
            prompt,
            **kwargs
        )


        # Save experience
        try:
            self.memory.set_working(
                "last_prompt",
                prompt
            )

            self.memory.set_working(
                "last_response",
                response.content
            )

        except Exception:
            pass


        return {
            "response": response.content,
            "model": response.model,
            "memory_used": len(memories)
        }


    async def shutdown(self):

        if self.providers:
            await self.providers.shutdown()

        self.memory.close()
