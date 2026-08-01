import pytest

from core.providers.provider_manager import ProviderManager
from core.providers.provider_base import (
    ProviderBase,
    ProviderConfig,
    ProviderResponse,
)


class FailingProvider(ProviderBase):

    async def generate(self, prompt: str, **kwargs):
        raise Exception("provider failed")

    async def get_model_info(self):
        return {
            "name": "failing"
        }


class WorkingProvider(ProviderBase):

    async def generate(self, prompt: str, **kwargs):
        return ProviderResponse(
            content="fallback success",
            model="working-model",
        )

    async def get_model_info(self):
        return {
            "name": "working"
        }


@pytest.mark.asyncio
async def test_provider_fallback():

    manager = ProviderManager()

    await manager.register(
        "fail",
        FailingProvider(
            ProviderConfig(
                api_key="test",
                model_name="fail",
            )
        ),
        priority=1,
    )

    await manager.register(
        "work",
        WorkingProvider(
            ProviderConfig(
                api_key="test",
                model_name="work",
            )
        ),
        priority=2,
    )

    result = await manager.generate(
        "hello"
    )

    assert result.content == "fallback success"
    assert result.model == "working-model"

    assert manager.status["fail"].failures == 1
    assert manager.status["work"].successes == 1

    await manager.shutdown()
