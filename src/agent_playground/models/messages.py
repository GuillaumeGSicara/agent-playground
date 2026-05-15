from typing import Literal

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self


class ToolCallFunction(BaseModel):
    name: str = Field(..., description="Function name to call")
    arguments: str = Field(..., description="JSON-encoded function arguments")


class ToolCallParam(BaseModel):
    id: str = Field(..., min_length=1, description="Unique tool call identifier assigned by the LLM")
    type: Literal["function"] = Field(default="function", description="Tool call type")
    function: ToolCallFunction = Field(..., description="Function call details")


class SystemMessage(BaseModel):
    role: Literal["system"] = Field(default="system", description="Message role")
    content: str = Field(..., description="System instruction content")


class TextContentPart(BaseModel):
    type: Literal["text"] = Field(default="text", description="Content part type")
    text: str = Field(..., description="Plain text segment")


class ImageUrl(BaseModel):
    url: str = Field(..., description="data: URI or HTTPS URL of the image")


class ImageContentPart(BaseModel):
    type: Literal["image_url"] = Field(default="image_url", description="Content part type")
    image_url: ImageUrl = Field(..., description="Image source for the LLM")


UserMessageContent = str | list[TextContentPart | ImageContentPart]


class UserMessage(BaseModel):
    role: Literal["user"] = Field(default="user", description="Message role")
    content: UserMessageContent = Field(..., description="Text or multimodal content parts")


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = Field(default="assistant", description="Message role")
    content: str | None = Field(default=None, description="Response text; None when tool_calls is present")
    tool_calls: list[ToolCallParam] | None = Field(default=None, description="Tool calls requested by the assistant")

    @model_validator(mode="after")
    def content_or_tool_calls_required(self) -> Self:
        if self.content is None and not self.tool_calls:
            raise ValueError("AssistantMessage must have either content or tool_calls")
        return self


class ToolMessage(BaseModel):
    role: Literal["tool"] = Field(default="tool", description="Message role")
    tool_call_id: str = Field(..., description="ID of the tool call this message responds to")
    content: str = Field(..., description="Tool execution result as a string")


LLMMessage = SystemMessage | UserMessage | AssistantMessage | ToolMessage
