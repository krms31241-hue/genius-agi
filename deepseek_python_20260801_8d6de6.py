"""
Decision Engine for Genius Core.

This module integrates with the existing executive package.
It uses the real ExecutiveEngine class from executive.executive_engine.
"""

import logging
from typing import Optional

from core.genius.models import Decision, RequestContext
from executive.executive_engine import ExecutiveEngine

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Decision Engine that delegates to the existing ExecutiveEngine.

    The ExecutiveEngine must have a 'decide' method that accepts
    request and classification arguments, returning a decision structure.
    """

    def __init__(self, executive: Optional[ExecutiveEngine] = None) -> None:
        """
        Initialize the decision engine.

        Args:
            executive: An instance of ExecutiveEngine. If not provided,
                a default instance is created.
        """
        self.executive = executive or ExecutiveEngine()
        logger.info("DecisionEngine initialized with ExecutiveEngine")

    async def decide(self, context: RequestContext) -> Decision:
        """
        Use the ExecutiveEngine to make a decision based on the request context.

        Args:
            context: The request context containing user request and classification.

        Returns:
            Decision object with action, payload, and provider requirements.

        Raises:
            RuntimeError: If the executive does not return a valid decision structure.
        """
        result = await self.executive.decide(
            request=context.user_request,
            classification=context.classification,
        )

        # Convert result to Decision
        if isinstance(result, dict):
            return Decision(
                action=result.get("action", "call_provider"),
                payload=result.get("payload", {}),
                reasoning=result.get("reasoning", ""),
                requires_provider=result.get("requires_provider", False),
                provider_hint=result.get("provider_hint"),
            )
        else:
            # If result is an object, extract attributes
            return Decision(
                action=getattr(result, "action", "call_provider"),
                payload=getattr(result, "payload", {}),
                reasoning=getattr(result, "reasoning", ""),
                requires_provider=getattr(result, "requires_provider", False),
                provider_hint=getattr(result, "provider_hint", None),
            )