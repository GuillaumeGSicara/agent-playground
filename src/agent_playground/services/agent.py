import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any

from loguru import logger
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall
from pydantic import BaseModel, Field

from agent_playground.constants import MAX_REACT_ITERATIONS
from agent_playground.infrastructure.llm import LLMClient
from agent_playground.models.events import (
    AgentEvent,
    TextChunkEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEvent,
)
from agent_playground.models.messages import (
    AssistantMessage,
    LLMMessage,
    SystemMessage,
    ToolCallFunction,
    ToolCallParam,
    ToolMessage,
    UserMessage,
    UserMessageContent,
)
from agent_playground.models.tools import ToolDefinition, ToolProvider
from agent_playground.prompts import load_prompt


class PendingToolCall(BaseModel):
    id: str = Field(default="", description="The unique identifier for the tool call")
    name: str = Field(default="", description="The name of the tool to be called")
    args: str = Field(default="", description="The accumulated JSON arguments string for the tool call")


class _StepState(BaseModel):
    finish_reason: str | None = Field(default=None, description="The reason the LLM finished the current turn")
    pending_tool_calls: dict[int, PendingToolCall] = Field(
        default_factory=dict, description="A mapping of tool call indices to their pending state"
    )
    response_text: str = Field(default="", description="The accumulated text response from the LLM")


class Agent:
    def __init__(
        self,
        llm_client: LLMClient,
        tool_providers: list[ToolProvider],
        max_context_tokens: int = 100_000,
    ) -> None:
        self._llm: LLMClient = llm_client
        self._tool_providers: list[ToolProvider] = tool_providers
        self._tool_definitions: list[ToolDefinition] = []
        self._max_context_tokens: int = max_context_tokens

    @staticmethod
    def _estimate_tokens(messages: list[LLMMessage]) -> int:
        return sum(len(str(m.model_dump())) for m in messages) // 4

    def _trim_history(self, history: list[LLMMessage], reserved_tokens: int) -> list[LLMMessage]:
        budget: int = int(self._max_context_tokens * 0.85) - reserved_tokens
        if budget <= 0:
            return []
        kept: list[LLMMessage] = []
        used: int = 0
        for msg in reversed(history):
            cost: int = self._estimate_tokens([msg])
            if used + cost > budget:
                break
            kept.append(msg)
            used += cost
        if len(kept) < len(history):
            logger.warning(
                "History trimmed: kept {}/{} messages to fit within {} token budget",
                len(kept),
                len(history),
                self._max_context_tokens,
            )
        return list(reversed(kept))

    async def _ensure_tools(self) -> None:
        if not self._tool_definitions:
            for provider in self._tool_providers:
                self._tool_definitions += await provider.list_definitions()

    def _build_initial_messages(
        self,
        user_content: UserMessageContent,
        history: list[LLMMessage] | None = None,
    ) -> list[LLMMessage]:
        system: SystemMessage = SystemMessage(role="system", content=load_prompt("system_prompt"))
        user: UserMessage = UserMessage(role="user", content=user_content)
        reserved: int = self._estimate_tokens([system, user])
        trimmed: list[LLMMessage] = self._trim_history(history or [], reserved)
        return [system, *trimmed, user]

    def _process_tool_call_delta(
        self,
        tc: ChoiceDeltaToolCall,
        pending: dict[int, PendingToolCall],
        message_id: str,
    ) -> list[AgentEvent]:
        idx: int = tc.index
        if idx not in pending:
            return self._init_pending_tool_call(tc, pending, message_id)
        return self._update_pending_tool_call(tc, pending[idx])

    def _init_pending_tool_call(
        self,
        tc: ChoiceDeltaToolCall,
        pending: dict[int, PendingToolCall],
        message_id: str,
    ) -> list[AgentEvent]:
        tc_id: str = tc.id or ""
        tc_name: str = (tc.function.name or "") if tc.function else ""
        pending[tc.index] = PendingToolCall(id=tc_id, name=tc_name, args="")
        logger.info("Tool call started — tool={}, id={}", tc_name, tc_id)
        return [ToolCallStartEvent(tool_call_id=tc_id, tool_name=tc_name, parent_message_id=message_id)]

    def _update_pending_tool_call(
        self,
        tc: ChoiceDeltaToolCall,
        pending: PendingToolCall,
    ) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        if tc.id and not pending.id:
            pending.id = tc.id
        if tc.function and tc.function.name and not pending.name:
            pending.name = tc.function.name
        if tc.function and tc.function.arguments:
            pending.args += tc.function.arguments
            events.append(ToolCallArgsEvent(tool_call_id=pending.id, delta=tc.function.arguments))
        return events

    async def _stream_llm_response(
        self,
        messages: list[LLMMessage],
        state: _StepState,
    ) -> AsyncGenerator[AgentEvent, None]:
        message_id: str = str(uuid.uuid4())

        async for chunk in self._llm.stream_chat(messages, self._tool_definitions):
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            if choice.finish_reason:
                state.finish_reason = choice.finish_reason
            if choice.delta.content:
                state.response_text += choice.delta.content
                yield TextChunkEvent(message_id=message_id, delta=choice.delta.content)
            if choice.delta.tool_calls:
                for tc in choice.delta.tool_calls:
                    for event in self._process_tool_call_delta(tc, state.pending_tool_calls, message_id):
                        yield event

    async def _yield_tool_results(
        self,
        messages: list[LLMMessage],
        pending: dict[int, PendingToolCall],
    ) -> AsyncGenerator[AgentEvent, None]:
        for v in pending.values():
            yield ToolCallEndEvent(tool_call_id=v.id)
            result: str = await self._execute_tool(v.name, v.args)
            logger.info("Tool result received — tool={}", v.name)
            logger.debug("Tool result (first 200 chars): {:.200}", result)
            yield ToolResultEvent(tool_call_id=v.id, result=result)
            messages.append(ToolMessage(role="tool", tool_call_id=v.id, content=result))

    async def run(
        self,
        user_content: UserMessageContent,
        history: list[LLMMessage] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        logger.info("Agent run started")
        await self._ensure_tools()
        messages: list[LLMMessage] = self._build_initial_messages(user_content, history)

        for i in range(MAX_REACT_ITERATIONS):
            logger.debug("ReAct iteration {}/{}", i + 1, MAX_REACT_ITERATIONS)
            state: _StepState = _StepState()
            async for event in self._stream_llm_response(messages, state):
                yield event
            if state.finish_reason != "tool_calls":
                logger.info("Agent run completed — iterations={}, finish_reason={}", i + 1, state.finish_reason)
                break
            messages.append(
                AssistantMessage(
                    role="assistant",
                    content=state.response_text or None,
                    tool_calls=[
                        ToolCallParam(id=v.id, function=ToolCallFunction(name=v.name, arguments=v.args))
                        for v in state.pending_tool_calls.values()
                    ],
                )
            )
            async for event in self._yield_tool_results(messages, state.pending_tool_calls):
                yield event

    async def _execute_tool(self, tool_name: str, args_json: str) -> str:
        logger.debug("Executing '{}' with args: {}", tool_name, args_json)
        try:
            args: dict[str, Any] = json.loads(args_json)
        except json.JSONDecodeError:
            logger.warning("Cannot parse args for '{}': {}", tool_name, args_json)
            return f"Error: could not parse arguments for {tool_name}"
        for provider in self._tool_providers:
            result: str | None = await provider.handle_call(tool_name, args)
            if result is not None:
                return result
        return f"Error: unknown tool '{tool_name}'"
