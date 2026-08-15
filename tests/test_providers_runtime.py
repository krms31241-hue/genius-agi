"""Smoke tests for the provider bootstrap."""

import asyncio
import unittest

from core.bootstrap.providers_bootstrap import ProvidersBootstrap


class TestProvidersBootstrap(unittest.IsolatedAsyncioTestCase):
    async def test_initializes_local_provider_and_shuts_down(self):
        bootstrap = ProvidersBootstrap()
        manager = await bootstrap.initialize()

        self.assertEqual(len(manager.providers), 1)
        self.assertEqual(manager.active_provider.name, "local")
        self.assertEqual(manager.active_provider.model, "genius-local-v1")

        await manager.shutdown()
