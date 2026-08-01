"""
Genius AGI - Model Registry

Central registry for every AI model known by Genius.
The router queries this registry to decide which model
is most suitable for a given task.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    VLLM = "vllm"
    LOCAL = "local"
    GENIUS = "genius"


class ModelType(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class TaskType(str, Enum):
    CHAT = "chat"
    CODING = "coding"
    REASONING = "reasoning"
    VISION = "vision"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    EMBEDDING = "embedding"
    SEARCH = "search"
    TRANSLATION = "translation"
    DOCUMENT = "document"
    AGENT = "agent"


@dataclass(slots=True)
class ModelInfo:
    name: str
    provider: Provider
    model_type: ModelType

    enabled: bool = True

    context_window: int = 8192
    max_output_tokens: int = 4096

    coding_score: int = 0
    reasoning_score: int = 0
    vision_score: int = 0
    speed_score: int = 0
    cost_score: int = 0

    supports_tools: bool = False
    supports_json: bool = False
    supports_streaming: bool = False
    supports_images: bool = False
    supports_audio: bool = False

    tags: List[str] = field(default_factory=list)


class ModelRegistry:

    def __init__(self) -> None:
        self._models: Dict[str, ModelInfo] = {}

    def register(self, model: ModelInfo) -> None:
        self._models[model.name] = model

    def unregister(self, model_name: str) -> None:
        self._models.pop(model_name, None)

    def get(self, model_name: str) -> Optional[ModelInfo]:
        return self._models.get(model_name)

    def exists(self, model_name: str) -> bool:
        return model_name in self._models

    def all(self) -> List[ModelInfo]:
        return list(self._models.values())

    def enabled(self) -> List[ModelInfo]:
        return [m for m in self._models.values() if m.enabled]

    def provider_models(self, provider: Provider) -> List[ModelInfo]:
        return [
            m
            for m in self._models.values()
            if m.provider == provider
        ]

    def online(self) -> List[ModelInfo]:
        return [
            m
            for m in self._models.values()
            if m.model_type == ModelType.ONLINE
        ]

    def offline(self) -> List[ModelInfo]:
        return [
            m
            for m in self._models.values()
            if m.model_type == ModelType.OFFLINE
        ]

    def best_for(self, task: TaskType) -> List[ModelInfo]:

        models = self.enabled()

        if task == TaskType.CODING:
            return sorted(
                models,
                key=lambda m: (
                    m.coding_score,
                    m.reasoning_score,
                    m.speed_score,
                ),
                reverse=True,
            )

        if task == TaskType.REASONING:
            return sorted(
                models,
                key=lambda m: (
                    m.reasoning_score,
                    m.context_window,
                ),
                reverse=True,
            )

        if task == TaskType.VISION:
            return sorted(
                [
                    m
                    for m in models
                    if m.supports_images
                ],
                key=lambda m: (
                    m.vision_score,
                    m.reasoning_score,
                ),
                reverse=True,
            )

        return sorted(
            models,
            key=lambda m: (
                m.reasoning_score,
                m.speed_score,
            ),
            reverse=True,
        )


registry = ModelRegistry()

registry.register(
    ModelInfo(
        name="gpt-5",
        provider=Provider.OPENAI,
        model_type=ModelType.ONLINE,
        context_window=200000,
        coding_score=100,
        reasoning_score=100,
        vision_score=95,
        speed_score=80,
        cost_score=20,
        supports_streaming=True,
        supports_tools=True,
        supports_json=True,
        supports_images=True,
    )
)

registry.register(
    ModelInfo(
        name="claude-opus",
        provider=Provider.ANTHROPIC,
        model_type=ModelType.ONLINE,
        context_window=200000,
        coding_score=95,
        reasoning_score=99,
        vision_score=90,
        speed_score=75,
        cost_score=25,
        supports_streaming=True,
        supports_tools=True,
        supports_json=True,
        supports_images=True,
    )
)

registry.register(
    ModelInfo(
        name="gemini-2.5-pro",
        provider=Provider.GEMINI,
        model_type=ModelType.ONLINE,
        context_window=1000000,
        coding_score=92,
        reasoning_score=94,
        vision_score=100,
        speed_score=88,
        cost_score=35,
        supports_streaming=True,
        supports_tools=True,
        supports_json=True,
        supports_images=True,
        supports_audio=True,
    )
)

registry.register(
    ModelInfo(
        name="deepseek-r1",
        provider=Provider.OPENROUTER,
        model_type=ModelType.ONLINE,
        context_window=128000,
        coding_score=98,
        reasoning_score=96,
        speed_score=90,
        cost_score=95,
        supports_streaming=True,
        supports_json=True,
    )
)

registry.register(
    ModelInfo(
        name="qwen3",
        provider=Provider.OLLAMA,
        model_type=ModelType.OFFLINE,
        context_window=32768,
        coding_score=90,
        reasoning_score=90,
        speed_score=95,
        cost_score=100,
        supports_json=True,
    )
)

registry.register(
    ModelInfo(
        name="llama3",
        provider=Provider.LOCAL,
        model_type=ModelType.OFFLINE,
        context_window=8192,
        coding_score=80,
        reasoning_score=82,
        speed_score=97,
        cost_score=100,
    )
)

