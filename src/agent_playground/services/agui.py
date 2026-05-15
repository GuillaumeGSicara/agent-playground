import base64
import io
import uuid
from collections.abc import AsyncGenerator
from typing import Any, Union

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
    ToolCallArgsEvent as AguiToolCallArgsEvent,
    ToolCallEndEvent as AguiToolCallEndEvent,
    ToolCallResultEvent as AguiToolCallResultEvent,
    ToolCallStartEvent as AguiToolCallStartEvent,
)
from ag_ui.core import UserMessage as AguiUserMessage
from ag_ui.encoder import EventEncoder
from pypdf import PdfReader
from starlette.requests import Request
from starlette.responses import StreamingResponse

from agent_playground.services.agent import Agent
from agent_playground.services.protocols import ConversationStoreProtocol
from agent_playground.models.events import (
    AgentEvent,
    TextChunkEvent,
    ToolCallArgsEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    ToolResultEvent,
)
from agent_playground.models.messages import (
    ImageContentPart,
    ImageUrl,
    TextContentPart,
    UserMessageContent,
)


def _to_user_content(raw: Union[str, list[InputContent]]) -> UserMessageContent:
    if isinstance(raw, str):
        return raw
    parts: list[TextContentPart | ImageContentPart] = []
    for part in raw:
        if isinstance(part, TextInputContent):
            parts.append(TextContentPart(text=part.text))
        elif isinstance(part, ImageInputContent):
            if isinstance(part.source, InputContentDataSource):
                url: str = f"data:{part.source.mime_type};base64,{part.source.value}"
            else:
                url = part.source.value
            parts.append(ImageContentPart(image_url=ImageUrl(url=url)))
        elif isinstance(part, DocumentInputContent):
            parts.append(_pdf_to_text_part(part))
    return parts


def _pdf_to_text_part(doc: DocumentInputContent) -> TextContentPart:
    if isinstance(doc.source, InputContentDataSource):
        pdf_bytes: bytes = base64.b64decode(doc.source.value)
    else:
        pdf_bytes = base64.b64decode(doc.source.value)
    reader: PdfReader = PdfReader(io.BytesIO(pdf_bytes))
    text: str = "\n".join(page.extract_text() or "" for page in reader.pages)
    return TextContentPart(text=f"[PDF content]\n{text}")


def _content_summary(content: UserMessageContent) -> str:
    if isinstance(content, str):
        return content
    for part in content:
        if isinstance(part, TextContentPart):
            return part.text
    return ""


class AguiHandler:
    def __init__(self, agent: Agent, conversation_store: ConversationStoreProtocol) -> None:
        self._agent: Agent = agent
        self._conversation_store: ConversationStoreProtocol = conversation_store

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

        ag_user_messages: list[AguiUserMessage] = [m for m in input_data.messages if m.role == "user"]
        user_content: UserMessageContent = _to_user_content(ag_user_messages[-1].content) if ag_user_messages else ""
        self._conversation_store.record(input_data.thread_id, _content_summary(user_content))

        state: dict[str, Any] = {
            "message_id": str(uuid.uuid4()),
            "message_started": False,
        }

        try:
            async for event in self._agent.run(user_content):
                async for encoded_event in self._handle_agent_event(event, state, encoder):
                    yield encoded_event

            if state["message_started"]:
                yield encoder.encode(TextMessageEndEvent(message_id=state["message_id"]))

            yield encoder.encode(RunFinishedEvent(thread_id=input_data.thread_id, run_id=input_data.run_id))

        except Exception as exc:
            yield encoder.encode(RunErrorEvent(message=str(exc)))

    async def _handle_agent_event(
        self,
        event: AgentEvent,
        state: dict[str, Any],
        encoder: EventEncoder,
    ) -> AsyncGenerator[str, None]:
        if isinstance(event, TextChunkEvent):
            if not state["message_started"]:
                yield encoder.encode(TextMessageStartEvent(message_id=state["message_id"], role="assistant"))
                state["message_started"] = True
            yield encoder.encode(TextMessageContentEvent(message_id=state["message_id"], delta=event.delta))
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
