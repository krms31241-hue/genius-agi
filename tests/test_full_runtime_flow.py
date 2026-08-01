import pytest

from runtime.genius_runtime import GeniusRuntime


@pytest.mark.asyncio
async def test_full_runtime_flow():
    runtime = GeniusRuntime()

    await runtime.initialize()

    result = await runtime.run(
        "عرف نفسك في سطر واحد"
    )

    await runtime.shutdown()

    assert result is not None
    assert result["response"]
    assert result["model"]
