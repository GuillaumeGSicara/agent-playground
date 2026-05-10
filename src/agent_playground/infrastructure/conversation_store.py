from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ConversationSummary:
    thread_id: str
    last_user_message: str
    last_activity: str  # ISO 8601
    run_count: int


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
            last_activity=datetime.now(timezone.utc).isoformat(),
            run_count=run_count,
        )

    def all(self) -> list[ConversationSummary]:
        return sorted(
            self._threads.values(),
            key=lambda c: c.last_activity,
            reverse=True,
        )
