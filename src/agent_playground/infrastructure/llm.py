from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
from pydantic import SecretStr

from agent_playground.models.messages import LLMMessage
from agent_playground.models.tools import ToolDefinition


class LLMClient:
    def __init__(self, base_url: str, api_key: SecretStr, model_name: str) -> None:
        self._client: AsyncOpenAI = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key.get_secret_value(),
        )
        self._model_name: str = model_name

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        messages_data: list[dict[str, Any]] = [m.model_dump(exclude_none=True) for m in messages]
        kwargs: dict[str, Any] = {
            "model": self._model_name,
            "messages": messages_data,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = [t.model_dump() for t in tools]

        stream = await self._client.chat.completions.create(**kwargs)
        async for chunk in stream:
            yield chunk
