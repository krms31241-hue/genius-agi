import pytest

from runtime.genius_runtime import GeniusRuntime


@pytest.mark.asyncio
async def test_gemini_runtime_response():
    runtime = GeniusRuntime()

    await runtime.initialize()

    result = await runtime.run(
        "اكتب جملة قصيرة تعرف فيها نفسك"
    )

    await runtime.shutdown()

    assert result["response"]
    assert result["model"]
