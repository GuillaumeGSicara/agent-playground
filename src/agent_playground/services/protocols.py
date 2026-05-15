from typing import Protocol

from agent_playground.models.conversations import ConversationSummary


class ConversationStoreProtocol(Protocol):
    def record(self, thread_id: str, last_user_message: str) -> None: ...
    def all(self) -> list[ConversationSummary]: ...
