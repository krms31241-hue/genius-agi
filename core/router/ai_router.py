"""Route requests through a bounded, read-only tool loop."""

from __future__ import annotations

import ast
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful general-purpose assistant. Use tools only when they improve "
    "the answer. Tools are read-only and cannot access external systems. Never claim "
    "to have completed an action you did not perform."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Read relevant memory snippets supplied for this request.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
]


@dataclass
class AIResponse:
    content: str
    model: str
    agent: str = "general"
    tokens_used: int = 0
    tool_calls: int = 0


def _calculate(expression: str) -> str:
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Constant)
    tree = ast.parse(expression, mode="eval")
    if not all(isinstance(node, allowed) for node in ast.walk(tree)):
        raise ValueError("Only arithmetic expressions are allowed")
    return str(eval(compile(tree, "<calculation>", "eval"), {"__builtins__": {}}, {}))


class AIRouter:
    def __init__(self, providers: Any) -> None:
        self.providers = providers
        self.routing_history: list[tuple[str, AIResponse]] = []

    def _run_tool(self, name: str, arguments: dict[str, Any], memories: list[dict[str, Any]]) -> str:
        if name == "calculate":
            return _calculate(arguments["expression"])
        if name == "recall_memory":
            return json.dumps(memories[:5], ensure_ascii=False)
        raise ValueError("Tool is not allowed")

    async def generate(self, prompt: str, **kwargs: Any) -> AIResponse:
        provider = self.providers.active_provider
        if provider is None:
            raise RuntimeError("No AI provider is configured")
        agent = kwargs.get("agent", "general")

        if not hasattr(provider, "complete"):
            content = await provider.generate(prompt, **kwargs)
            response = AIResponse(content=content, model=provider.model, agent=agent)
            self.routing_history.append((prompt, response))
            return response

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        memories = kwargs.get("relevant_memories", [])
        tool_calls = 0
        for _ in range(3):
            raw = await provider.complete(messages, tools=TOOLS)
            message = raw["choices"][0]["message"]
            calls = message.get("tool_calls") or []
            if not calls:
                response = AIResponse(
                    content=message.get("content") or "I could not generate a response.",
                    model=raw.get("model", provider.model),
                    agent=agent,
                    tokens_used=raw.get("usage", {}).get("total_tokens", 0),
                    tool_calls=tool_calls,
                )
                self.routing_history.append((prompt, response))
                return response

            messages.append(message)
            for call in calls:
                tool_calls += 1
                try:
                    arguments = json.loads(call["function"].get("arguments") or "{}")
                    result = self._run_tool(call["function"]["name"], arguments, memories)
                except (ValueError, KeyError, json.JSONDecodeError, SyntaxError) as exc:
                    result = f"Tool error: {exc}"
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

        raise RuntimeError("Agent exceeded the maximum of three tool rounds")
