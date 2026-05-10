from pydantic import BaseModel, Field


class TextChunkEvent(BaseModel):
    message_id: str = Field(..., description="ID of the message this chunk belongs to")
    delta: str = Field(..., min_length=1, description="Incremental text content streamed from the LLM")


class ToolCallStartEvent(BaseModel):
    tool_call_id: str = Field(..., min_length=1, description="Unique identifier for this tool call")
    tool_name: str = Field(..., min_length=1, description="Name of the tool being invoked")
    parent_message_id: str = Field(..., description="ID of the assistant message that triggered this call")


class ToolCallArgsEvent(BaseModel):
    tool_call_id: str = Field(..., description="Tool call identifier")
    delta: str = Field(..., description="Incremental JSON fragment for the tool call arguments")


class ToolCallEndEvent(BaseModel):
    tool_call_id: str = Field(..., description="Tool call identifier, signals argument streaming is complete")


class ToolResultEvent(BaseModel):
    tool_call_id: str = Field(..., description="Tool call identifier this result responds to")
    result: str = Field(..., description="Tool execution result as a plain string")


AgentEvent = TextChunkEvent | ToolCallStartEvent | ToolCallArgsEvent | ToolCallEndEvent | ToolResultEvent
