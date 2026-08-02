"""
Genius Core Package - Phase 1 of the new Genius AGI architecture.

This package provides the orchestration layer that sits between the user
and the underlying providers, ensuring that all responses are processed
through the Genius brain.
"""

from core.genius.conversation_brain import ConversationBrain
from core.genius.decision_engine import DecisionEngine
from core.genius.genius_core import GeniusCore
from core.genius.models import (
    ClassificationResult,
    ConversationState,
    Decision,
    EvaluationResult,
    RequestContext,
    TaskType,
)
from core.genius.provider_selector import ProviderSelector
from core.genius.response_evaluator import ResponseEvaluator
from core.genius.task_classifier import TaskClassifier

__all__ = [
    "GeniusCore",
    "TaskClassifier",
    "ProviderSelector",
    "ResponseEvaluator",
    "ConversationBrain",
    "DecisionEngine",
    "RequestContext",
    "TaskType",
    "ClassificationResult",
    "EvaluationResult",
    "Decision",
    "ConversationState",
]
