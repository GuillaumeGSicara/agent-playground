from datetime import datetime

from pydantic import BaseModel, Field


class ConversationSummary(BaseModel):
    thread_id: str = Field(..., description="The unique identifier for the conversation thread")
    last_user_message: str = Field(..., description="The content of the last message sent by the user")
    last_activity: datetime = Field(..., description="The timestamp of the last activity in this thread")
    run_count: int = Field(..., description="The number of times the agent has been run in this thread")
