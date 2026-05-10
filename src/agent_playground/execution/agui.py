import uuid
from collections.abc import AsyncGenerator

from ag_ui.core import (
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
    ToolCallArgsEvent as AguiToolCallArgsEvent,
    ToolCallEndEvent as AguiToolCallEndEvent,
    ToolCallResultEvent as AguiToolCallResultEvent,
    ToolCallStartEvent as AguiToolCallStartEvent,
)
from ag_ui.encoder import EventEncoder
from starlette.requests import Request
from starlette.responses import StreamingResponse

from agent_playground.execution.agent import Agent
from agent_playground.infrastructure.conversation_store import ConversationStore
from agent_playground.models.events import (
    AgentEvent,
    TextChunkEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEvent,
)


class AguiHandler:
    def __init__(self, agent: Agent, conversation_store: ConversationStore) -> None:
        self._agent: Agent = agent
        self._conversation_store: ConversationStore = conversation_store

    async def handle(self, request: Request) -> StreamingResponse:
        body: dict[str, object] = await request.json()
        input_data: RunAgentInput = RunAgentInput.model_validate(body)
        encoder: EventEncoder = EventEncoder(accept=request.headers.get("accept", ""))

        return StreamingResponse(
            self._generate_events(input_data, encoder),
            media_type=encoder.get_content_type(),
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def _generate_events(
        self,
        input_data: RunAgentInput,
        encoder: EventEncoder,
    ) -> AsyncGenerator[str, None]:
        yield encoder.encode(RunStartedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id))

        user_messages = [m for m in input_data.messages if m.role == "user"]
        user_text: str = str(user_messages[-1].content) if user_messages else ""
        self._conversation_store.record(input_data.thread_id, user_text)
        message_id: str = str(uuid.uuid4())
        message_started: bool = False

        try:
            event: AgentEvent
            async for event in self._agent.run(user_text):
                if isinstance(event, TextChunkEvent):
                    if not message_started:
                        yield encoder.encode(TextMessageStartEvent(message_id=message_id, role="assistant"))
                        message_started = True
                    yield encoder.encode(TextMessageContentEvent(message_id=message_id, delta=event.delta))

                elif isinstance(event, ToolCallStartEvent):
                    yield encoder.encode(
                        AguiToolCallStartEvent(
                            tool_call_id=event.tool_call_id,
                            tool_call_name=event.tool_name,
                            parent_message_id=event.parent_message_id,
                        )
                    )

                elif isinstance(event, ToolCallArgsEvent):
                    yield encoder.encode(AguiToolCallArgsEvent(tool_call_id=event.tool_call_id, delta=event.delta))

                elif isinstance(event, ToolCallEndEvent):
                    yield encoder.encode(AguiToolCallEndEvent(tool_call_id=event.tool_call_id))

                elif isinstance(event, ToolResultEvent):
                    yield encoder.encode(
                        AguiToolCallResultEvent(
                            message_id=str(uuid.uuid4()),
                            tool_call_id=event.tool_call_id,
                            content=event.result,
                            role="tool",
                        )
                    )

            if message_started:
                yield encoder.encode(TextMessageEndEvent(message_id=message_id))

            yield encoder.encode(RunFinishedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id))

        except Exception as exc:
            yield encoder.encode(RunErrorEvent(message=str(exc)))
