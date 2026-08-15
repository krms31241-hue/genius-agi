"""Vercel AI Gateway provider using the OpenAI-compatible Chat Completions API."""

from __future__ import annotations

import json
from typing import Any



class AIGatewayProvider:
    """Minimal async provider with optional tool-call responses."""

    endpoint = "https://ai-gateway.vercel.sh/v1/chat/completions"

    def __init__(self, api_key: str, model: str) -> None:
        self.name = "ai-gateway"
        self.model = model
        self.api_key = api_key

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools

        import aiohttp

        timeout = aiohttp.ClientTimeout(total=60)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.endpoint, json=payload, headers=headers) as response:
                body = await response.text()
                if response.status >= 400:
                    raise RuntimeError(f"AI Gateway request failed ({response.status})")
                return json.loads(body)

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        response = await self.complete(
            [{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.2),
            max_tokens=kwargs.get("max_tokens", 1024),
        )
        return response["choices"][0]["message"].get("content") or ""

    async def shutdown(self) -> None:
        return None
