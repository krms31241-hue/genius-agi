"""
Strongly‑typed data models for the Genius Core.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskType(str, Enum):
    """Supported task categories."""
    CHAT = "chat"
    REASONING = "reasoning"
    CODING = "coding"
    ARCHITECTURE = "architecture"
    RESEARCH = "research"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    DOCUMENTATION = "documentation"
    SELF_EVOLUTION = "self_evolution"
    LEARNING = "learning"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClassificationResult:
    """Result of task classification."""
    task_type: TaskType
    confidence: float
    complexity: float
    estimated_tokens: int
    recommended_provider: Optional[str] = None
    reasoning: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if not 0.0 <= self.complexity <= 1.0:
            raise ValueError("complexity must be between 0 and 1")
        if self.estimated_tokens < 0:
            raise ValueError("estimated_tokens must be non‑negative")


@dataclass(frozen=True)
class ProviderSelection:
    """Selected provider with metadata."""
    provider_name: str
    model_name: str
    priority: int
    estimated_cost: float
    estimated_latency: float
    reasoning: str = ""


@dataclass(frozen=True)
class EvaluationResult:
    """Result of response evaluation."""
    passed: bool
    score: float
    feedback: str = ""
    requires_regeneration: bool = False
    regeneration_reason: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0 and 1")


@dataclass(frozen=True)
class RequestContext:
    """Immutable context for a single request."""
    # Non-default fields first
    conversation_id: str
    user_request: str
    # Then fields with defaults
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    classification: Optional[ClassificationResult] = None
    selected_provider: Optional[ProviderSelection] = None
    provider_response: Optional[str] = None
    final_response: Optional[str] = None
    reasoning_path: List[str] = field(default_factory=list)
    timings: Dict[str, float] = field(default_factory=dict)

    def add_timing(self, step: str, duration: float) -> RequestContext:
        new_timings = dict(self.timings)
        new_timings[step] = duration
        return RequestContext(
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            timestamp=self.timestamp,
            user_request=self.user_request,
            classification=self.classification,
            selected_provider=self.selected_provider,
            provider_response=self.provider_response,
            final_response=self.final_response,
            reasoning_path=self.reasoning_path,
            timings=new_timings,
        )

    def add_reasoning_step(self, step: str) -> RequestContext:
        new_path = self.reasoning_path + [step]
        return RequestContext(
            request_id=self.request_id,
            conversation_id=self.conversation_id,
            timestamp=self.timestamp,
            user_request=self.user_request,
            classification=self.classification,
            selected_provider=self.selected_provider,
            provider_response=self.provider_response,
            final_response=self.final_response,
            reasoning_path=new_path,
            timings=self.timings,
        )


@dataclass
class ConversationState:
    """State for a single conversation."""
    conversation_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_history: List[str] = field(default_factory=list)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    temporary_memory: Dict[str, Any] = field(default_factory=dict)
    context_window: List[Dict[str, Any]] = field(default_factory=list)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def add_reasoning(self, step: str) -> None:
        self.reasoning_history.append(step)

    def add_execution(self, execution: Dict[str, Any]) -> None:
        self.execution_history.append(execution)

    def get_context(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        return self.messages[-max_messages:]


@dataclass(frozen=True)
class Decision:
    """Decision made by the Executive Engine."""
    action: str
    payload: Dict[str, Any]
    reasoning: str = ""
    requires_provider: bool = False
    provider_hint: Optional[str] = None