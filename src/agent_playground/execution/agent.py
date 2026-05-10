import json
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall

from agent_playground.constants import MAX_REACT_ITERATIONS, SYSTEM_PROMPT, ToolName
from agent_playground.infrastructure.llm import LLMClient
from agent_playground.infrastructure.search import WebSearchTool
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
)


@dataclass
class _StepState:
    finish_reason: str | None = None
    pending_tool_calls: dict[int, dict[str, str]] = field(default_factory=dict)
    response_text: str = ""


class Agent:
    def __init__(self, llm_client: LLMClient, search_tool: WebSearchTool) -> None:
        self._llm: LLMClient = llm_client
        self._search_tool: WebSearchTool = search_tool

    def _build_initial_messages(
        self,
        user_message: str,
        history: list[LLMMessage] | None,
    ) -> list[LLMMessage]:
        return [
            SystemMessage(role="system", content=SYSTEM_PROMPT),
            *(history or []),
            UserMessage(role="user", content=user_message),
        ]

    def _process_tool_call_delta(
        self,
        tc: ChoiceDeltaToolCall,
        pending: dict[int, dict[str, str]],
        message_id: str,
    ) -> list[AgentEvent]:
        events: list[AgentEvent] = []
        idx: int = tc.index
        if idx not in pending:
            tc_id: str = tc.id or ""
            tc_name: str = (tc.function.name or "") if tc.function else ""
            pending[idx] = {"id": tc_id, "name": tc_name, "args": ""}
            events.append(ToolCallStartEvent(tool_call_id=tc_id, tool_name=tc_name, parent_message_id=message_id))
        else:
            if tc.id and not pending[idx]["id"]:
                pending[idx]["id"] = tc.id
            if tc.function and tc.function.name and not pending[idx]["name"]:
                pending[idx]["name"] = tc.function.name
        if tc.function and tc.function.arguments:
            pending[idx]["args"] += tc.function.arguments
            events.append(ToolCallArgsEvent(tool_call_id=pending[idx]["id"], delta=tc.function.arguments))
        return events

    async def _stream_llm_response(
        self,
        messages: list[LLMMessage],
        state: _StepState,
    ) -> AsyncGenerator[AgentEvent, None]:
        message_id: str = str(uuid.uuid4())
        async for chunk in self._llm.stream_chat(messages, [self._search_tool.definition]):
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
        pending: dict[int, dict[str, str]],
    ) -> AsyncGenerator[AgentEvent, None]:
        for v in pending.values():
            yield ToolCallEndEvent(tool_call_id=v["id"])
            result: str = await self._execute_tool(v["name"], v["args"])
            yield ToolResultEvent(tool_call_id=v["id"], result=result)
            messages.append(ToolMessage(role="tool", tool_call_id=v["id"], content=result))

    async def run(
        self,
        user_message: str,
        history: list[LLMMessage] | None = None,
    ) -> AsyncGenerator[AgentEvent, None]:
        messages: list[LLMMessage] = self._build_initial_messages(user_message, history)

        for _ in range(MAX_REACT_ITERATIONS):
            state: _StepState = _StepState()
            async for event in self._stream_llm_response(messages, state):
                yield event
            if state.finish_reason != "tool_calls":
                break
            messages.append(
                AssistantMessage(
                    role="assistant",
                    content=state.response_text or None,
                    tool_calls=[
                        ToolCallParam(id=v["id"], function=ToolCallFunction(name=v["name"], arguments=v["args"]))
                        for v in state.pending_tool_calls.values()
                    ],
                )
            )
            async for event in self._yield_tool_results(messages, state.pending_tool_calls):
                yield event

    async def _execute_tool(self, tool_name: str, args_json: str) -> str:
        if tool_name == ToolName.WEB_SEARCH:
            try:
                args: dict[str, str] = json.loads(args_json)
                return await self._search_tool.run(args.get("query", ""))
            except json.JSONDecodeError:
                return f"Error: could not parse arguments for {tool_name}"
        return f"Error: unknown tool '{tool_name}'"
