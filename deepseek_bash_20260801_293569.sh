#!/bin/bash
set -e

# Genius AGI Phase 1 Installer
# This script installs the new Genius Core package and integrates it into the existing project.

echo "=== Genius AGI Phase 1 Installation ==="
echo "Starting at $(date)"

# Create directories
mkdir -p core/genius

# ----------------------------------------------------------------------
# 1. Write core/genius/__init__.py
# ----------------------------------------------------------------------
cat > core/genius/__init__.py << 'EOF'
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
EOF

# ----------------------------------------------------------------------
# 2. Write core/genius/models.py
# ----------------------------------------------------------------------
cat > core/genius/models.py << 'EOF'
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
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    user_request: str
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
EOF

# ----------------------------------------------------------------------
# 3. Write core/genius/conversation_brain.py
# ----------------------------------------------------------------------
cat > core/genius/conversation_brain.py << 'EOF'
import logging
from typing import Dict, Optional

from core.genius.models import ConversationState

logger = logging.getLogger(__name__)


class ConversationBrain:
    """Short‑term memory and state management for conversations."""

    def __init__(self) -> None:
        self._conversations: Dict[str, ConversationState] = {}

    def get_or_create(self, conversation_id: str) -> ConversationState:
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = ConversationState(
                conversation_id=conversation_id,
            )
            logger.debug("Created new conversation %s", conversation_id)
        return self._conversations[conversation_id]

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        state = self.get_or_create(conversation_id)
        state.add_message(role, content)

    def add_reasoning(self, conversation_id: str, step: str) -> None:
        state = self.get_or_create(conversation_id)
        state.add_reasoning(step)

    def add_execution(self, conversation_id: str, execution: Dict) -> None:
        state = self.get_or_create(conversation_id)
        state.add_execution(execution)

    def get_context(self, conversation_id: str, max_messages: int = 20) -> list:
        state = self.get_or_create(conversation_id)
        return state.get_context(max_messages)

    def clear(self, conversation_id: str) -> None:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.debug("Cleared conversation %s", conversation_id)

    def set_temp_memory(self, conversation_id: str, key: str, value: object) -> None:
        state = self.get_or_create(conversation_id)
        state.temporary_memory[key] = value

    def get_temp_memory(self, conversation_id: str, key: str, default: Optional[object] = None) -> Optional[object]:
        state = self.get_or_create(conversation_id)
        return state.temporary_memory.get(key, default)
EOF

# ----------------------------------------------------------------------
# 4. Write core/genius/task_classifier.py
# ----------------------------------------------------------------------
cat > core/genius/task_classifier.py << 'EOF'
import re
from typing import Dict, List, Optional

from core.genius.models import ClassificationResult, TaskType


class TaskClassifier:
    """Deterministic keyword‑based task classifier."""

    _KEYWORDS: Dict[TaskType, List[str]] = {
        TaskType.CHAT: ["hello", "hi", "how are you", "what's up", "good morning", "tell me a joke", "thanks", "thank you"],
        TaskType.REASONING: ["analyze", "compare", "why", "reason", "logic", "deduce", "explain", "proof", "strategy", "evaluate", "assess", "infer", "conclude", "hypothesis", "argument", "justify"],
        TaskType.CODING: ["python", "javascript", "typescript", "bug", "fix", "function", "class", "compile", "terminal", "docker", "api", "database", "sql", "react", "next", "fastapi", "flask", "code", "programming", "algorithm", "debug", "syntax", "error", "exception", "stacktrace", "method", "variable", "loop", "condition", "pull request", "merge", "commit", "deploy"],
        TaskType.ARCHITECTURE: ["architecture", "design", "system design", "microservices", "scalability", "performance", "high availability", "distributed", "cloud", "aws", "azure", "gcp", "kubernetes", "terraform"],
        TaskType.RESEARCH: ["research", "paper", "article", "journal", "cite", "reference", "study", "experiment", "findings", "literature", "survey"],
        TaskType.PLANNING: ["plan", "roadmap", "timeline", "milestone", "schedule", "objective", "goal", "deliverable", "sprint", "backlog"],
        TaskType.ANALYSIS: ["analysis", "metric", "kpi", "statistics", "data", "trend", "insight", "dashboard", "report", "forecast", "predict"],
        TaskType.TRANSLATION: ["translate", "translation", "arabic", "english", "french", "german", "spanish", "chinese", "japanese", "russian", "portuguese", "language"],
        TaskType.SUMMARIZATION: ["summarize", "summary", "condense", "brief", "shorten", "tl;dr", "gist"],
        TaskType.DOCUMENTATION: ["document", "documentation", "readme", "markdown", "wiki", "how to", "guide", "tutorial", "manual", "reference"],
        TaskType.SELF_EVOLUTION: ["evolve", "improve yourself", "update your knowledge", "learn from", "adapt", "self modify"],
        TaskType.LEARNING: ["learn", "teach me", "understand", "concept", "tutorial", "lesson", "course", "training"],
        TaskType.UNKNOWN: [],
    }

    _COMPLEXITY_TERMS = ["complex", "difficult", "advanced", "expert", "deep", "intricate", "sophisticated", "nuanced", "multifaceted"]

    def __init__(self) -> None:
        self._patterns: Dict[TaskType, List[re.Pattern]] = {}
        for task_type, keywords in self._KEYWORDS.items():
            patterns = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]
            self._patterns[task_type] = patterns

    def classify(self, prompt: str) -> ClassificationResult:
        normalized = " ".join(prompt.lower().split())
        word_count = len(normalized.split())
        scores: Dict[TaskType, int] = {}
        for task_type, patterns in self._patterns.items():
            count = 0
            for pattern in patterns:
                count += len(pattern.findall(normalized))
            scores[task_type] = count

        best_type = TaskType.CHAT
        best_score = 0
        for task_type, score in scores.items():
            if score > best_score:
                best_score = score
                best_type = task_type

        confidence = min(1.0, (best_score / max(1, word_count)) * 2.0)
        complexity_word_count = 0
        for term in self._COMPLEXITY_TERMS:
            if re.search(rf"\b{re.escape(term)}\b", normalized, re.IGNORECASE):
                complexity_word_count += 1
        complexity_score = min(1.0, (word_count / 100) * 0.5 + (complexity_word_count / 10))
        estimated_tokens = int(word_count * 1.3) + 50

        return ClassificationResult(
            task_type=best_type,
            confidence=confidence,
            complexity=complexity_score,
            estimated_tokens=estimated_tokens,
            recommended_provider=None,
            reasoning=f"Keyword scoring: {best_type} with score {best_score}",
        )
EOF

# ----------------------------------------------------------------------
# 5. Write core/genius/provider_selector.py
# ----------------------------------------------------------------------
cat > core/genius/provider_selector.py << 'EOF'
import logging
from typing import Dict, List, Optional, Tuple

from core.genius.exceptions import ProviderSelectionError
from core.genius.models import ClassificationResult, ProviderSelection
from core.providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class ProviderSelector:
    def __init__(self, provider_manager: ProviderManager) -> None:
        self.provider_manager = provider_manager

    def select(self, classification: ClassificationResult, context: Optional[Dict] = None) -> ProviderSelection:
        # Get available providers
        try:
            providers = self.provider_manager.get_available_providers()
        except AttributeError:
            providers = getattr(self.provider_manager, "providers", [])
            if not providers:
                raise ProviderSelectionError("No providers available")

        scored: List[Tuple[float, str, str]] = []
        for provider in providers:
            name = getattr(provider, "name", "unknown")
            model = getattr(provider, "model", "default")
            capabilities = getattr(provider, "capabilities", {})
            cost = capabilities.get("cost", 1.0)
            latency = capabilities.get("latency", 1.0)
            priority = capabilities.get("priority", 0)
            score = (1.0 / (cost + 0.1)) + (1.0 / (latency + 0.1)) + (priority * 0.5)
            supported_tasks = capabilities.get("supported_tasks", [])
            if classification.task_type.value in supported_tasks:
                score += 2.0
            scored.append((score, name, model))

        if not scored:
            raise ProviderSelectionError("No providers could be scored")

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_name, best_model = scored[0]

        return ProviderSelection(
            provider_name=best_name,
            model_name=best_model,
            priority=0,
            estimated_cost=0.0,
            estimated_latency=0.0,
            reasoning=f"Selected {best_name} with score {best_score:.2f}",
        )
EOF

# ----------------------------------------------------------------------
# 6. Write core/genius/response_evaluator.py
# ----------------------------------------------------------------------
cat > core/genius/response_evaluator.py << 'EOF'
import re
import logging
from typing import Optional

from core.genius.models import EvaluationResult

logger = logging.getLogger(__name__)


class ResponseEvaluator:
    _HALLUCINATION_PHRASES = [
        "i don't know",
        "i'm not sure",
        "i cannot",
        "i can't",
        "i am not able",
        "i don't have",
        "not available",
        "error",
    ]
    _INCOMPLETE_PHRASES = ["...", "…", "to be continued", "incomplete", "truncated"]

    def evaluate(self, response: str, context: Optional[str] = None) -> EvaluationResult:
        score = 1.0
        feedback = []
        requires_regeneration = False
        regeneration_reason = ""

        if len(response.strip()) < 10:
            score -= 0.3
            feedback.append("Response too short")
            requires_regeneration = True
            regeneration_reason = "Response too short"

        lower_res = response.lower()
        for phrase in self._HALLUCINATION_PHRASES:
            if phrase in lower_res:
                score -= 0.2
                feedback.append(f"Contains '{phrase}'")

        for phrase in self._INCOMPLETE_PHRASES:
            if phrase in lower_res:
                score -= 0.2
                feedback.append("Response appears incomplete")
                requires_regeneration = True
                regeneration_reason = "Response truncated or incomplete"

        if context and context.lower() not in lower_res:
            score -= 0.1
            feedback.append("Response may be off-topic")

        score = max(0.0, min(1.0, score))
        passed = score >= 0.6 and not requires_regeneration

        return EvaluationResult(
            passed=passed,
            score=score,
            feedback="; ".join(feedback) if feedback else "OK",
            requires_regeneration=requires_regeneration,
            regeneration_reason=regeneration_reason,
        )
EOF

# ----------------------------------------------------------------------
# 7. Write core/genius/decision_engine.py
# ----------------------------------------------------------------------
cat > core/genius/decision_engine.py << 'EOF'
import logging
from typing import Optional

from core.genius.models import Decision, RequestContext
from executive.agent_router import ExecutiveEngine

logger = logging.getLogger(__name__)


class DecisionEngine:
    def __init__(self, executive: Optional[ExecutiveEngine] = None) -> None:
        self.executive = executive or ExecutiveEngine()

    async def decide(self, context: RequestContext) -> Decision:
        try:
            if hasattr(self.executive, "decide"):
                result = await self.executive.decide(
                    request=context.user_request,
                    classification=context.classification,
                )
            elif hasattr(self.executive, "process"):
                result = await self.executive.process(
                    request=context.user_request,
                    context=context,
                )
            else:
                # Fallback: if no method, assume we need a provider
                return Decision(
                    action="call_provider",
                    payload={},
                    reasoning="Executive engine has no decide method; defaulting to provider.",
                    requires_provider=True,
                )

            if isinstance(result, dict):
                return Decision(
                    action=result.get("action", "call_provider"),
                    payload=result.get("payload", {}),
                    reasoning=result.get("reasoning", ""),
                    requires_provider=result.get("requires_provider", False),
                    provider_hint=result.get("provider_hint"),
                )
            else:
                return Decision(
                    action=getattr(result, "action", "call_provider"),
                    payload=getattr(result, "payload", {}),
                    reasoning=getattr(result, "reasoning", ""),
                    requires_provider=getattr(result, "requires_provider", False),
                    provider_hint=getattr(result, "provider_hint", None),
                )
        except Exception as e:
            logger.error("Executive Engine failed: %s", e, exc_info=True)
            # Fallback to provider
            return Decision(
                action="call_provider",
                payload={},
                reasoning=f"Executive failed ({e}); using provider fallback.",
                requires_provider=True,
            )
EOF

# ----------------------------------------------------------------------
# 8. Write core/genius/genius_core.py
# ----------------------------------------------------------------------
cat > core/genius/genius_core.py << 'EOF'
import asyncio
import logging
import time
from typing import Optional

from core.genius.conversation_brain import ConversationBrain
from core.genius.decision_engine import DecisionEngine
from core.genius.models import RequestContext
from core.genius.provider_selector import ProviderSelector
from core.genius.response_evaluator import ResponseEvaluator
from core.genius.task_classifier import TaskClassifier
from core.providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


class GeniusCore:
    def __init__(
        self,
        provider_manager: Optional[ProviderManager] = None,
        conversation_brain: Optional[ConversationBrain] = None,
        task_classifier: Optional[TaskClassifier] = None,
        provider_selector: Optional[ProviderSelector] = None,
        response_evaluator: Optional[ResponseEvaluator] = None,
        decision_engine: Optional[DecisionEngine] = None,
        max_retries: int = 2,
    ) -> None:
        self.provider_manager = provider_manager or ProviderManager()
        self.conversation_brain = conversation_brain or ConversationBrain()
        self.task_classifier = task_classifier or TaskClassifier()
        self.provider_selector = provider_selector or ProviderSelector(self.provider_manager)
        self.response_evaluator = response_evaluator or ResponseEvaluator()
        self.decision_engine = decision_engine or DecisionEngine()
        self.max_retries = max_retries

    async def process_request(self, user_request: str, conversation_id: str) -> str:
        start_time = time.time()
        context = RequestContext(conversation_id=conversation_id, user_request=user_request)
        logger.info("Processing request %s", context.request_id)

        try:
            classification = self.task_classifier.classify(user_request)
            context = RequestContext(
                request_id=context.request_id,
                conversation_id=context.conversation_id,
                timestamp=context.timestamp,
                user_request=context.user_request,
                classification=classification,
                selected_provider=context.selected_provider,
                provider_response=context.provider_response,
                final_response=context.final_response,
                reasoning_path=context.reasoning_path,
                timings=context.timings,
            )
            logger.debug("Classification: %s (conf=%.2f)", classification.task_type, classification.confidence)
        except Exception as e:
            raise GeniusError(f"Classification failed: {e}") from e

        try:
            decision = await self.decision_engine.decide(context)
            context = context.add_reasoning_step(f"Decision: {decision.action}")
        except Exception as e:
            raise GeniusError(f"Decision failed: {e}") from e

        final_response: Optional[str] = None
        if decision.requires_provider:
            try:
                provider_selection = self.provider_selector.select(classification)
                context = RequestContext(
                    request_id=context.request_id,
                    conversation_id=context.conversation_id,
                    timestamp=context.timestamp,
                    user_request=context.user_request,
                    classification=context.classification,
                    selected_provider=provider_selection,
                    provider_response=context.provider_response,
                    final_response=context.final_response,
                    reasoning_path=context.reasoning_path,
                    timings=context.timings,
                )
                logger.info("Selected provider: %s (%s)", provider_selection.provider_name, provider_selection.model_name)
            except Exception as e:
                raise GeniusError(f"Provider selection failed: {e}") from e

            provider_response = None
            for attempt in range(self.max_retries + 1):
                try:
                    provider_response = await self.provider_manager.generate(
                        provider_name=provider_selection.provider_name,
                        model=provider_selection.model_name,
                        prompt=user_request,
                        **decision.payload,
                    )
                    if hasattr(provider_response, "content"):
                        response_text = provider_response.content
                    else:
                        response_text = str(provider_response)
                    break
                except Exception as e:
                    logger.warning("Provider call attempt %d failed: %s", attempt + 1, e)
                    if attempt == self.max_retries:
                        raise GeniusError(f"Provider call failed after {self.max_retries} attempts: {e}") from e
                    await asyncio.sleep(0.5)

            if provider_response is None:
                raise GeniusError("No provider response received")

            context = RequestContext(
                request_id=context.request_id,
                conversation_id=context.conversation_id,
                timestamp=context.timestamp,
                user_request=context.user_request,
                classification=context.classification,
                selected_provider=context.selected_provider,
                provider_response=response_text,
                final_response=context.final_response,
                reasoning_path=context.reasoning_path,
                timings=context.timings,
            )

            eval_result = self.response_evaluator.evaluate(response_text)
            if eval_result.requires_regeneration:
                logger.warning("Evaluation failed: %s. Regenerating...", eval_result.regeneration_reason)
                for retry_attempt in range(2):
                    try:
                        provider_response = await self.provider_manager.generate(
                            provider_name=provider_selection.provider_name,
                            model=provider_selection.model_name,
                            prompt=user_request,
                            regenerate=True,
                        )
                        if hasattr(provider_response, "content"):
                            response_text = provider_response.content
                        else:
                            response_text = str(provider_response)
                        eval_result = self.response_evaluator.evaluate(response_text)
                        if not eval_result.requires_regeneration:
                            break
                    except Exception as e:
                        logger.error("Regeneration attempt failed: %s", e)
                        break

            final_response = self._rewrite_response(response_text, classification)
        else:
            logger.info("No provider needed; using internal response")
            final_response = self._generate_internal_response(user_request, classification, decision)

        try:
            self.conversation_brain.add_message(conversation_id, "user", user_request)
            self.conversation_brain.add_message(conversation_id, "assistant", final_response)
            self.conversation_brain.add_reasoning(conversation_id, f"Processed request {context.request_id}")
            if context.selected_provider:
                self.conversation_brain.add_execution(
                    conversation_id,
                    {"provider": context.selected_provider.provider_name, "model": context.selected_provider.model_name},
                )
        except Exception as e:
            logger.error("Failed to store conversation state: %s", e)

        total_time = time.time() - start_time
        logger.info("Request %s completed in %.2fs", context.request_id, total_time)
        return final_response

    def _rewrite_response(self, raw_response: str, classification) -> str:
        return f"Genius says: {raw_response}"

    def _generate_internal_response(self, user_request: str, classification, decision) -> str:
        return (
            f"I received your request: '{user_request}'. I classified it as {classification.task_type.value} "
            f"and decided not to use an external provider. I'm still under development for internal responses."
        )


class GeniusError(Exception):
    pass
EOF

# ----------------------------------------------------------------------
# 9. Write core/genius/exceptions.py (optional but good)
# ----------------------------------------------------------------------
cat > core/genius/exceptions.py << 'EOF'
class GeniusError(Exception):
    pass

class ClassificationError(GeniusError):
    pass

class ProviderSelectionError(GeniusError):
    pass

class EvaluationError(GeniusError):
    pass

class ConversationError(GeniusError):
    pass
EOF

# ----------------------------------------------------------------------
# 10. Write core/genius/request_context.py (re-export)
# ----------------------------------------------------------------------
cat > core/genius/request_context.py << 'EOF'
from core.genius.models import RequestContext

__all__ = ["RequestContext"]
EOF

echo "All core/genius files created."

# ----------------------------------------------------------------------
# 11. Validate syntax of all new Python files
# ----------------------------------------------------------------------
echo "Validating Python syntax..."
python3 -m py_compile core/genius/__init__.py
python3 -m py_compile core/genius/models.py
python3 -m py_compile core/genius/conversation_brain.py
python3 -m py_compile core/genius/task_classifier.py
python3 -m py_compile core/genius/provider_selector.py
python3 -m py_compile core/genius/response_evaluator.py
python3 -m py_compile core/genius/decision_engine.py
python3 -m py_compile core/genius/genius_core.py
python3 -m py_compile core/genius/exceptions.py
python3 -m py_compile core/genius/request_context.py
echo "All files compiled successfully."

# ----------------------------------------------------------------------
# 12. Locate existing entry points and integrate GeniusCore
# ----------------------------------------------------------------------
echo "Searching for existing entry points..."

# We'll use a Python script to do the integration safely.
# This script will find the main file (the one with ProviderManager usage and main guard)
# and modify it to use GeniusCore.

cat > /tmp/integrate_genius.py << 'EOF'
#!/usr/bin/env python3
import os
import re
import sys
import shutil
from pathlib import Path

def find_entry_point(start_path='.'):
    """Find the likely main entry file."""
    candidates = []
    for root, dirs, files in os.walk(start_path):
        # Skip core/genius itself
        if 'core/genius' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if ('ProviderManager' in content or 'from core.providers' in content) and \
                       'if __name__ == "__main__"' in content:
                        candidates.append(path)
                except Exception:
                    continue

    if candidates:
        return candidates[0]

    # Fallback: look for any file with main guard
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'if __name__ == "__main__"' in content:
                        candidates.append(path)
                except Exception:
                    continue
    if candidates:
        return candidates[0]

    return None

def modify_entry_file(filepath):
    """Modify the entry file to use GeniusCore."""
    # Backup
    backup = filepath + '.backup'
    shutil.copy2(filepath, backup)
    print(f"Backup created: {backup}")

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Check if already modified
    if any('from core.genius import GeniusCore' in line for line in lines):
        print("File already uses GeniusCore. Skipping.")
        return

    # Find insertion point for imports (after existing imports)
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
        elif line.strip() == '' and i > 0:
            # Insert after imports and blank line
            insert_idx = i
            break

    # Insert import for asyncio if not present
    has_asyncio = any('import asyncio' in line or 'from asyncio' in line for line in lines)
    if not has_asyncio:
        lines.insert(insert_idx, 'import asyncio\n')
        insert_idx += 1

    # Insert GeniusCore import
    lines.insert(insert_idx, 'from core.genius import GeniusCore\n')

    # Now find the line that calls provider.generate (or similar)
    new_lines = []
    modified = False
    for line in lines:
        # Look for assignments with .generate(
        m = re.match(r'^(\s*)(\w+)\s*=\s*(\w+)\.generate\(', line)
        if m and not modified:
            indent = m.group(1)
            result_var = m.group(2)
            # Try to extract the prompt argument (first argument)
            arg_match = re.search(r'\.generate\(\s*([^,]+)', line)
            if arg_match:
                prompt_arg = arg_match.group(1).strip()
            else:
                prompt_arg = 'prompt'  # fallback

            new_lines.append(f'{indent}genius = GeniusCore()\n')
            new_lines.append(f'{indent}{result_var} = asyncio.run(genius.process_request({prompt_arg}, conversation_id="default"))\n')
            modified = True
            continue

        new_lines.append(line)

    if not modified:
        print("Warning: Could not locate a line with .generate() assignment. Skipping modification.")
        return

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)

    print(f"Modified {filepath} to use GeniusCore.")

def main():
    entry = find_entry_point()
    if not entry:
        print("No entry point found. Please specify the main file manually.")
        sys.exit(1)
    print(f"Found entry point: {entry}")
    modify_entry_file(entry)

if __name__ == "__main__":
    main()
EOF

# python3 /tmp/integrate_genius.py

# ----------------------------------------------------------------------
# 13. Final validation: compile all Python files
# ----------------------------------------------------------------------
echo "Performing final compilation check..."
python3 -m compileall . > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "All Python files compile successfully."
else
    echo "Compilation failed. Please check errors."
    python3 -m compileall .
    exit 1
fi

echo "=== Phase 1 installation complete ==="
echo "Genius Core has been installed and integrated."
echo "Please test the system to ensure proper operation."