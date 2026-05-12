from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    """A summary of an AG-UI conversation thread."""

    thread_id: str = Field(..., description="The unique identifier for the conversation thread")
    last_user_message: str = Field(..., description="The content of the last message sent by the user")
    last_activity: datetime = Field(..., description="The timestamp of the last activity in this thread")
    run_count: int = Field(..., description="The number of times the agent has been run in this thread")


class ConversationStore:
    """In-memory registry of AG-UI conversation threads."""

    def __init__(self) -> None:
        self._threads: dict[str, ConversationSummary] = {}

    def record(self, thread_id: str, last_user_message: str) -> None:
        existing: ConversationSummary | None = self._threads.get(thread_id)
        run_count: int = (existing.run_count + 1) if existing else 1
        self._threads[thread_id] = ConversationSummary(
            thread_id=thread_id,
            last_user_message=last_user_message[:200],
            last_activity=datetime.now(timezone.utc),
            run_count=run_count,
        )

    def all(self) -> list[ConversationSummary]:
        return sorted(
            self._threads.values(),
            key=lambda c: c.last_activity,
            reverse=True,
        )
