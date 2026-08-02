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
