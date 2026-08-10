"""AI Router - Intelligent routing of prompts to appropriate agents"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AIResponse:
    """Structured AI response"""
    content: str
    model: str
    agent: str = "general"
    tokens_used: int = 0

class AIRouter:
    """Routes prompts to appropriate AI providers and agents"""
    
    def __init__(self, providers):
        self.providers = providers
        self.routing_history = []
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """Generate response using appropriate provider"""
        logger.info(f"Routing prompt: {prompt[:50]}...")
        
        # Get context if available
        resource_context = kwargs.get('resource_context', {})
        agent = kwargs.get('agent', 'general')
        
        # Route to active provider
        if self.providers and hasattr(self.providers, 'active_provider'):
            provider = self.providers.active_provider
            content = await provider.generate(prompt, **kwargs)
        else:
            content = f"Processed: {prompt[:100]}..."
        
        response = AIResponse(
            content=content,
            model=getattr(self.providers, 'active_provider', None).model if hasattr(self.providers, 'active_provider') else "unknown",
            agent=agent
        )
        
        self.routing_history.append((prompt, response))
        return response
