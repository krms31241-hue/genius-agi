import pytest

from core.providers.provider_manager import ProviderManager
from core.providers.provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
)


class MockProvider(ProviderBase):

    async def generate(self, prompt: str, **kwargs):
        return ProviderResponse(
            content="mock response",
            model="mock-model",
        )

    async def get_model_info(self):
        return {
            "name": "mock-model"
        }


@pytest.mark.asyncio
async def test_provider_registration():

    manager = ProviderManager()

    provider = MockProvider(
        ProviderConfig(
            api_key="test",
            model_name="mock-model",
        )
    )

    await manager.register(
        "mock",
        provider,
    )

    assert "mock" in manager.providers

    loaded = manager.get("mock")

    assert loaded is provider

    await manager.shutdown()
