import base64
import io
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from ag_ui.core import (
    DocumentInputContent,
    ImageInputContent,
    InputContent,
    InputContentDataSource,
    RunAgentInput,
    RunErrorEvent,
    RunFinishedEvent,
    RunStartedEvent,
    TextInputContent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    TextMessageStartEvent,
)
from ag_ui.core import (
    Message as AguiMessage,
)
from ag_ui.core import (
    ToolCallArgsEvent as AguiToolCallArgsEvent,
)
from ag_ui.core import (
    ToolCallEndEvent as AguiToolCallEndEvent,
)
from ag_ui.core import (
    ToolCallResultEvent as AguiToolCallResultEvent,
)
from ag_ui.core import (
    ToolCallStartEvent as AguiToolCallStartEvent,
)
from ag_ui.core import (
    UserMessage as AguiUserMessage,
)
from ag_ui.encoder import EventEncoder
from loguru import logger
from pypdf import PdfReader
from starlette.requests import Request
from starlette.responses import StreamingResponse

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
    ImageContentPart,
    ImageUrl,
    LLMMessage,
    TextContentPart,
    ToolCallFunction,
    ToolCallParam,
    ToolMessage,
    UserMessage,
    UserMessageContent,
)
from agent_playground.services.agent import Agent


def _to_history(messages: list[AguiMessage]) -> list[LLMMessage]:
    history: list[LLMMessage] = []
    for msg in messages:
        if msg.role == "user" and isinstance(msg.content, (str, list)):
            history.append(UserMessage(content=_to_user_content(msg.content)))
        elif msg.role == "assistant":
            tool_calls: Any = getattr(msg, "tool_calls", None)
            if tool_calls:
                history.append(
                    AssistantMessage(
                        content=getattr(msg, "content", None) or None,
                        tool_calls=[
                            ToolCallParam(
                                id=tc.id,
                                function=ToolCallFunction(name=tc.function.name, arguments=tc.function.arguments),
                            )
                            for tc in tool_calls
                        ],
                    )
                )
            elif getattr(msg, "content", None):
                history.append(AssistantMessage(content=msg.content))
        elif msg.role == "tool":
            history.append(ToolMessage(tool_call_id=msg.tool_call_id, content=msg.content))
    return history


def _to_user_content(raw: str | list[InputContent]) -> UserMessageContent:
    if isinstance(raw, str):
        return raw

    parts: list[TextContentPart | ImageContentPart] = []

    for part in raw:
        match part:
            case TextInputContent():
                parts.append(TextContentPart(text=part.text))
            case ImageInputContent():
                if isinstance(part.source, InputContentDataSource):
                    url: str = f"data:{part.source.mime_type};base64,{part.source.value}"
                else:
                    url = part.source.value
                parts.append(ImageContentPart(image_url=ImageUrl(url=url)))
            case DocumentInputContent():
                parts.append(_pdf_to_text_part(part))
            case _:
                raise TypeError(f"Unsupported input content type: {type(part).__name__}")
    return parts


def _pdf_to_text_part(doc: DocumentInputContent) -> TextContentPart:
    if isinstance(doc.source, InputContentDataSource):
        pdf_bytes: bytes = base64.b64decode(doc.source.value)
    else:
        pdf_bytes = base64.b64decode(doc.source.value)
    reader: PdfReader = PdfReader(io.BytesIO(pdf_bytes))
    text: str = "\n".join(page.extract_text() or "" for page in reader.pages)
    return TextContentPart(text=f"[PDF content]\n{text}")


@dataclass
class _GenerationState:
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_started: bool = False


class AguiHandler:
    def __init__(self, agent: Agent) -> None:
        self._agent: Agent = agent

    async def handle(self, request: Request) -> StreamingResponse:
        body: dict[str, Any] = await request.json()
        input_data: RunAgentInput = RunAgentInput.model_validate(body)
        logger.debug("POST /invocations — thread={}, run={}", input_data.thread_id, input_data.run_id)
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
        logger.info("Run started — thread={}, run={}", input_data.thread_id, input_data.run_id)

        all_msgs: list[AguiMessage] = input_data.messages
        user_msgs: list[AguiUserMessage] = [m for m in all_msgs if m.role == "user"]
        last_user_msg: AguiUserMessage | None = user_msgs[-1] if user_msgs else None
        last_user_idx: int = (
            len(all_msgs) - 1 - next(i for i, m in enumerate(reversed(all_msgs)) if m.role == "user")
            if last_user_msg
            else -1
        )
        user_content: UserMessageContent = _to_user_content(last_user_msg.content) if last_user_msg else ""
        history: list[LLMMessage] = _to_history(all_msgs[:last_user_idx])

        state: _GenerationState = _GenerationState()

        try:
            async for event in self._agent.run(user_content, history=history):
                async for encoded_event in self._handle_agent_event(event, state, encoder):
                    yield encoded_event

            if state.message_started:
                yield encoder.encode(TextMessageEndEvent(message_id=state.message_id))

            yield encoder.encode(RunFinishedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id))
            logger.info("Run finished — thread={}, run={}", input_data.thread_id, input_data.run_id)

        except Exception as exc:
            logger.exception("Run error — thread={}, run={}", input_data.thread_id, input_data.run_id)
            yield encoder.encode(RunErrorEvent(message=str(exc)))

    async def _handle_agent_event(
        self,
        event: AgentEvent,
        state: _GenerationState,
        encoder: EventEncoder,
    ) -> AsyncGenerator[str, None]:
        if isinstance(event, TextChunkEvent):
            if not state.message_started:
                yield encoder.encode(TextMessageStartEvent(message_id=state.message_id, role="assistant"))
                state.message_started = True
            yield encoder.encode(TextMessageContentEvent(message_id=state.message_id, delta=event.delta))
        elif isinstance(event, ToolCallStartEvent | ToolCallArgsEvent | ToolCallEndEvent | ToolResultEvent):
            async for encoded in self._handle_tool_event(event, encoder):
                yield encoded

    async def _handle_tool_event(
        self,
        event: AgentEvent,
        encoder: EventEncoder,
    ) -> AsyncGenerator[str, None]:
        if isinstance(event, ToolCallStartEvent):
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
