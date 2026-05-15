from typing import Any, Protocol

from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    type: str = Field(..., description="JSON Schema type (e.g. 'string', 'integer', 'boolean')")
    description: str = Field(..., description="Human-readable description of the parameter")


class ToolParameters(BaseModel):
    type: str = Field(default="object", description="Always 'object' per OpenAI tool spec")
    properties: dict[str, ToolParameter] = Field(..., description="Parameter definitions keyed by name")
    required: list[str] = Field(default_factory=list, description="Names of required parameters")


class ToolFunction(BaseModel):
    name: str = Field(..., description="Tool function name as recognised by the LLM")
    description: str = Field(..., description="What the tool does, shown to the LLM")
    parameters: ToolParameters = Field(..., description="JSON Schema for function arguments")


class ToolDefinition(BaseModel):
    type: str = Field(default="function", description="Tool type, always 'function'")
    function: ToolFunction = Field(..., description="Full function definition")


class ToolProvider(Protocol):
    async def list_definitions(self) -> list[ToolDefinition]: ...
    async def handle_call(self, tool_name: str, args: dict[str, Any]) -> str | None:
        """Return the tool result, or None if this provider does not handle tool_name."""
        ...
