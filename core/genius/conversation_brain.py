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
