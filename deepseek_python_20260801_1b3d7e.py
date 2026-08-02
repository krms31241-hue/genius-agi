"""
Decision Engine for Genius Core.

This module provides the decision-making capability by delegating to the
existing executive module. It automatically discovers the correct executive
class from the project's executive.agent_router.
"""

import logging
from typing import Any, Optional, Type, Union

from core.genius.models import Decision, RequestContext

logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# Auto-discovery of the executive class from executive.agent_router
# ----------------------------------------------------------------------

# Try to import the correct executive class
# Common names: ExecutiveEngine, AgentRouter, Router, Executive, AgentManager
_executive_class: Optional[Type] = None
_executive_module = None

try:
    # First attempt: import the module
    import executive.agent_router as _agent_router
    _executive_module = _agent_router

    # Try to get a class that is likely the executive
    candidates = [
        "ExecutiveEngine",
        "AgentRouter",
        "Router",
        "Executive",
        "AgentManager",
        "RouteManager",
    ]
    for name in candidates:
        if hasattr(_agent_router, name):
            _executive_class = getattr(_agent_router, name)
            logger.debug("Found executive class: %s in executive.agent_router", name)
            break

    if _executive_class is None:
        # If no known name, try to find any class defined in the module
        # that is not imported from elsewhere (heuristic: check for classes defined in the module)
        import inspect
        for attr_name in dir(_agent_router):
            attr = getattr(_agent_router, attr_name)
            if inspect.isclass(attr) and attr.__module__ == _agent_router.__name__:
                _executive_class = attr
                logger.debug("Auto-discovered executive class: %s", attr_name)
                break

except ImportError as e:
    logger.error("Could not import executive.agent_router: %s", e)
    # We'll raise a more informative error later

# If still None, raise a clear error
if _executive_class is None:
    raise ImportError(
        "Could not find any executive class in executive.agent_router. "
        "Please ensure the executive module is correctly installed."
    )


# ----------------------------------------------------------------------
# Decision Engine Implementation
# ----------------------------------------------------------------------

class DecisionEngine:
    """
    Decision Engine that delegates to the existing executive module.

    The executive class is auto-discovered from executive.agent_router.
    It must have a 'decide' or 'process' method that accepts a request
    and classification, returning a decision structure.
    """

    def __init__(self, executive: Optional[Any] = None) -> None:
        """
        Initialize the decision engine.

        Args:
            executive: An instance of the executive class. If not provided,
                an instance is created using the auto-discovered class.
        """
        if executive is None:
            # Instantiate the executive class (assuming no required constructor args)
            # If the constructor requires arguments, this will fail.
            # The user can pass an existing instance to avoid this.
            try:
                self.executive = _executive_class()
            except TypeError as e:
                raise TypeError(
                    f"Executive class {_executive_class.__name__} cannot be instantiated "
                    "without arguments. Please pass an existing executive instance."
                ) from e
        else:
            self.executive = executive

        logger.info("DecisionEngine initialized with executive: %s", self.executive.__class__.__name__)

    async def decide(self, context: RequestContext) -> Decision:
        """
        Use the executive to make a decision based on the request context.

        Args:
            context: The request context containing user request and classification.

        Returns:
            Decision object with action, payload, and provider requirements.

        Raises:
            RuntimeError: If the executive does not support a decision method.
        """
        # Try to call the appropriate method on the executive
        # Priority: decide, route, process
        method = None
        if hasattr(self.executive, "decide"):
            method = getattr(self.executive, "decide")
        elif hasattr(self.executive, "route"):
            method = getattr(self.executive, "route")
        elif hasattr(self.executive, "process"):
            method = getattr(self.executive, "process")

        if method is None:
            raise RuntimeError(
                f"Executive {self.executive.__class__.__name__} does not have "
                "'decide', 'route', or 'process' method."
            )

        try:
            # Call the method with the appropriate arguments
            # We'll try to pass the request and classification
            result = await method(
                request=context.user_request,
                classification=context.classification,
            )
        except TypeError as e:
            # If the method signature is different, try a simpler call
            logger.warning("Method call failed with signature, trying fallback: %s", e)
            try:
                result = await method(context.user_request)
            except Exception as e2:
                raise RuntimeError(f"Executive method call failed: {e2}") from e2

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
            # If result is an object, try to extract attributes
            return Decision(
                action=getattr(result, "action", "call_provider"),
                payload=getattr(result, "payload", {}),
                reasoning=getattr(result, "reasoning", ""),
                requires_provider=getattr(result, "requires_provider", False),
                provider_hint=getattr(result, "provider_hint", None),
            )