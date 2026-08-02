"""
Genius Core - The central brain of Genius AGI.

This module defines the main orchestrator that processes user requests
through classification, decision making, provider interaction, and evaluation.

It is designed to be independent of the existing runtime; dependencies are
injected via abstract interfaces for later integration.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from core.genius.models import (
    ClassificationResult,
    ConversationState,
    Decision,
    EvaluationResult,
    ProviderSelection,
    RequestContext,
    TaskType,
)

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Abstract Interfaces for Dependency Injection
# ----------------------------------------------------------------------

@runtime_checkable
class ProviderManagerInterface(Protocol):
    """Abstract interface for the provider manager."""

    async def generate(
        self,
        provider_name: str,
        model: str,
        prompt: str,
        **kwargs: Any,
    ) -> Any:
        """Generate a response from the given provider."""
        ...

    def get_available_providers(self) -> List[Any]:
        """Return a list of available providers."""
        ...


@runtime_checkable
class DecisionEngineInterface(Protocol):
    """Abstract interface for the decision engine."""

    async def decide(self, context: RequestContext) -> Decision:
        """Make a decision based on the request context."""
        ...


@runtime_checkable
class ConversationBrainInterface(Protocol):
    """Abstract interface for conversation state management."""

    def get_or_create(self, conversation_id: str) -> ConversationState:
        """Retrieve or create a conversation state."""
        ...

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """Add a message to the conversation history."""
        ...

    def add_reasoning(self, conversation_id: str, step: str) -> None:
        """Add a reasoning step."""
        ...

    def add_execution(self, conversation_id: str, execution: Dict[str, Any]) -> None:
        """Add an execution record."""
        ...

    def get_context(self, conversation_id: str, max_messages: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent messages for context."""
        ...

    def set_temp_memory(self, conversation_id: str, key: str, value: object) -> None:
        """Store temporary data."""
        ...

    def get_temp_memory(self, conversation_id: str, key: str, default: Optional[object] = None) -> Optional[object]:
        """Retrieve temporary data."""
        ...


@runtime_checkable
class TaskClassifierInterface(Protocol):
    """Abstract interface for task classification."""

    def classify(self, prompt: str) -> ClassificationResult:
        """Classify the given prompt."""
        ...


@runtime_checkable
class ProviderSelectorInterface(Protocol):
    """Abstract interface for provider selection."""

    def select(self, classification: ClassificationResult, context: Optional[Dict[str, Any]] = None) -> ProviderSelection:
        """Select the best provider for the given classification."""
        ...


@runtime_checkable
class ResponseEvaluatorInterface(Protocol):
    """Abstract interface for response evaluation."""

    def evaluate(self, response: str, context: Optional[str] = None) -> EvaluationResult:
        """Evaluate the quality of a provider response."""
        ...


# ----------------------------------------------------------------------
# Core Exceptions
# ----------------------------------------------------------------------

class GeniusError(Exception):
    """Base exception for all Genius Core errors."""


# ----------------------------------------------------------------------
# Genius Core Implementation
# ----------------------------------------------------------------------

class GeniusCore:
    """
    The main orchestrator for all user requests.

    Flow:
        1. Receive user request and conversation ID.
        2. Build RequestContext.
        3. Classify the task using TaskClassifier.
        4. Use DecisionEngine to decide the action.
        5. If provider is needed, use ProviderSelector to pick one.
        6. Call the provider via ProviderManager.
        7. Evaluate the response using ResponseEvaluator.
        8. Rewrite the response into Genius personality.
        9. Store conversation state.
        10. Return the final response.
    """

    def __init__(
        self,
        provider_manager: ProviderManagerInterface,
        conversation_brain: ConversationBrainInterface,
        task_classifier: TaskClassifierInterface,
        provider_selector: ProviderSelectorInterface,
        response_evaluator: ResponseEvaluatorInterface,
        decision_engine: DecisionEngineInterface,
        max_retries: int = 2,
    ) -> None:
        """
        Initialize the Genius Core with its dependencies.

        Args:
            provider_manager: The provider manager for external providers.
            conversation_brain: The conversation state manager.
            task_classifier: The task classifier.
            provider_selector: The provider selector.
            response_evaluator: The response evaluator.
            decision_engine: The decision engine (e.g., using Executive).
            max_retries: Maximum retries for provider calls if evaluation fails.
        """
        self.provider_manager = provider_manager
        self.conversation_brain = conversation_brain
        self.task_classifier = task_classifier
        self.provider_selector = provider_selector
        self.response_evaluator = response_evaluator
        self.decision_engine = decision_engine
        self.max_retries = max_retries
        self._closed = False
        self._lock = asyncio.Lock()

        logger.info("GeniusCore initialized with max_retries=%d", max_retries)

    async def process_request(self, user_request: str, conversation_id: str) -> str:
        """
        Process a user request and return the final Genius response.

        Args:
            user_request: The user's input text.
            conversation_id: The conversation ID for context.

        Returns:
            The final response string.

        Raises:
            GeniusError: If processing fails.
        """
        if self._closed:
            raise GeniusError("GeniusCore is closed and cannot process requests.")

        start_time = time.time()

        # 1. Build context
        context = RequestContext(
            conversation_id=conversation_id,
            user_request=user_request,
        )
        logger.info("Processing request %s", context.request_id)

        try:
            # 2. Classify the task
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
            logger.debug(
                "Classification: %s (conf=%.2f, comp=%.2f)",
                classification.task_type.value,
                classification.confidence,
                classification.complexity,
            )
        except Exception as e:
            logger.error("Classification failed: %s", e, exc_info=True)
            raise GeniusError(f"Classification failed: {e}") from e

        # 3. Decision
        try:
            decision = await self.decision_engine.decide(context)
            context = context.add_reasoning_step(f"Decision: {decision.action}")
            logger.debug("Decision: action=%s, requires_provider=%s", decision.action, decision.requires_provider)
        except Exception as e:
            logger.error("Decision failed: %s", e, exc_info=True)
            raise GeniusError(f"Decision failed: {e}") from e

        # 4. Process based on decision
        final_response: Optional[str] = None

        if decision.requires_provider:
            # 4a. Select provider
            try:
                provider_selection = self.provider_selector.select(
                    classification,
                    context={"decision": decision, "conversation_id": conversation_id},
                )
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
                logger.info(
                    "Selected provider: %s (%s)",
                    provider_selection.provider_name,
                    provider_selection.model_name,
                )
            except Exception as e:
                logger.error("Provider selection failed: %s", e, exc_info=True)
                raise GeniusError(f"Provider selection failed: {e}") from e

            # 4b. Call provider (with retries)
            provider_response = None
            response_text = ""
            for attempt in range(self.max_retries + 1):
                try:
                    # Build prompt from user request and any additional context from decision payload
                    prompt = user_request
                    # If decision payload has extra instructions, append them
                    if decision.payload.get("system_prompt"):
                        prompt = decision.payload["system_prompt"] + "\n" + prompt

                    provider_response = await self.provider_manager.generate(
                        provider_name=provider_selection.provider_name,
                        model=provider_selection.model_name,
                        prompt=prompt,
                        **{k: v for k, v in decision.payload.items() if k not in ("system_prompt",)},
                    )
                    # Extract text content
                    if hasattr(provider_response, "content"):
                        response_text = provider_response.content
                    elif isinstance(provider_response, str):
                        response_text = provider_response
                    else:
                        response_text = str(provider_response)
                    break
                except Exception as e:
                    logger.warning(
                        "Provider call attempt %d/%d failed: %s",
                        attempt + 1,
                        self.max_retries + 1,
                        e,
                    )
                    if attempt == self.max_retries:
                        raise GeniusError(f"Provider call failed after {self.max_retries} attempts: {e}") from e
                    await asyncio.sleep(0.5 * (attempt + 1))  # exponential backoff

            if provider_response is None:
                raise GeniusError("No provider response received")

            # Update context with provider response
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

            # 4c. Evaluate response
            eval_result = self.response_evaluator.evaluate(
                response_text,
                context=user_request,
            )
            if not eval_result.passed or eval_result.requires_regeneration:
                logger.warning(
                    "Evaluation failed: score=%.2f, feedback=%s. Regenerating...",
                    eval_result.score,
                    eval_result.feedback,
                )
                # Attempt regeneration (simple retry with a "regenerate" hint)
                for regen_attempt in range(2):
                    try:
                        provider_response = await self.provider_manager.generate(
                            provider_name=provider_selection.provider_name,
                            model=provider_selection.model_name,
                            prompt=user_request,
                            regenerate=True,
                            previous_response=response_text,
                            feedback=eval_result.feedback,
                        )
                        if hasattr(provider_response, "content"):
                            new_text = provider_response.content
                        elif isinstance(provider_response, str):
                            new_text = provider_response
                        else:
                            new_text = str(provider_response)
                        # Re-evaluate
                        new_eval = self.response_evaluator.evaluate(new_text, context=user_request)
                        if new_eval.passed and not new_eval.requires_regeneration:
                            response_text = new_text
                            eval_result = new_eval
                            break
                    except Exception as e:
                        logger.error("Regeneration attempt %d failed: %s", regen_attempt + 1, e)
                else:
                    logger.warning("Regeneration attempts exhausted; using original response.")

            # 4d. Rewrite response into Genius personality
            final_response = self._rewrite_response(response_text, classification)

        else:
            # 5. Internal response (no provider needed)
            logger.info("No provider needed; generating internal response.")
            final_response = self._generate_internal_response(
                user_request,
                classification,
                decision,
            )

        # 6. Store conversation state
        try:
            self.conversation_brain.add_message(conversation_id, "user", user_request)
            self.conversation_brain.add_message(conversation_id, "assistant", final_response)
            self.conversation_brain.add_reasoning(conversation_id, f"Processed request {context.request_id}")
            if context.selected_provider:
                self.conversation_brain.add_execution(
                    conversation_id,
                    {
                        "provider": context.selected_provider.provider_name,
                        "model": context.selected_provider.model_name,
                    },
                )
        except Exception as e:
            logger.error("Failed to store conversation state: %s", e)

        # 7. Log completion
        total_time = time.time() - start_time
        logger.info("Request %s completed in %.2fs", context.request_id, total_time)

        return final_response

    def _rewrite_response(self, raw_response: str, classification: ClassificationResult) -> str:
        """
        Rewrite the raw provider response to fit Genius's personality.

        In Phase 1, we simply add a prefix and optionally some formatting.
        Later, this can be more sophisticated.
        """
        # For now, a simple wrapper
        return f"Genius says: {raw_response}"

    def _generate_internal_response(
        self,
        user_request: str,
        classification: ClassificationResult,
        decision: Decision,
    ) -> str:
        """
        Generate a response without calling an external provider.

        This is a placeholder that can be replaced by more advanced reasoning.
        """
        return (
            f"I received your request: '{user_request}'. "
            f"I classified it as {classification.task_type.value} "
            f"and decided not to use an external provider. "
            f"Internal responses are under active development."
        )

    async def close(self) -> None:
        """
        Release any resources held by the core.
        """
        async with self._lock:
            if not self._closed:
                self._closed = True
                logger.info("Closing GeniusCore.")
                # Close dependencies if they have close methods
                for dep in [
                    self.provider_manager,
                    self.conversation_brain,
                    self.task_classifier,
                    self.provider_selector,
                    self.response_evaluator,
                    self.decision_engine,
                ]:
                    if hasattr(dep, "close") and callable(dep.close):
                        try:
                            await dep.close() if asyncio.iscoroutinefunction(dep.close) else dep.close()
                        except Exception as e:
                            logger.warning("Error closing dependency %s: %s", dep.__class__.__name__, e)
                self._closed = True

    async def __aenter__(self) -> "GeniusCore":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()