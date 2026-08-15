import unittest

from core.router.ai_router import AIRouter, _calculate


class FakeProvider:
    model = "test-model"
    def __init__(self): self.calls = 0
    async def complete(self, messages, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return {"model": self.model, "choices": [{"message": {"tool_calls": [{"id": "call_1", "function": {"name": "calculate", "arguments": '{"expression":"2 + 3 * 4"}'}}]}}]}
        return {"model": self.model, "usage": {"total_tokens": 12}, "choices": [{"message": {"content": "The result is 14."}}]}


class FakeBootstrap:
    active_provider = FakeProvider()


class TestAIRouter(unittest.IsolatedAsyncioTestCase):
    async def test_runs_bounded_calculation_tool_loop(self):
        router = AIRouter(FakeBootstrap())
        result = await router.generate("calculate", agent="general")
        self.assertEqual(result.content, "The result is 14.")
        self.assertEqual(result.tool_calls, 1)

    def test_calculator_rejects_names_and_calls(self):
        self.assertEqual(_calculate("2 + 3 * 4"), "14")
        with self.assertRaises(ValueError):
            _calculate("__import__('os').system('id')")
