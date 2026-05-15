from typing import Any

from loguru import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from agent_playground.models.tools import ToolDefinition, ToolFunction, ToolParameter, ToolParameters


class DatagouvMCPClient:
    def __init__(self, url: str) -> None:
        self._url: str = url
        self._cached_tool_names: set[str] = set()

    async def list_definitions(self) -> list[ToolDefinition]:
        logger.info("Fetching tool list from data.gouv.fr MCP — url={}", self._url)
        try:
            async with streamable_http_client(self._url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    tools: list[ToolDefinition] = [self._to_tool_definition(t) for t in result.tools]
                    self._cached_tool_names = {t.function.name for t in tools}
                    logger.info("data.gouv.fr MCP reported {} tool(s)", len(tools))
                    logger.debug("data.gouv.fr MCP tools: {}", list(self._cached_tool_names))
                    return tools
        except Exception:
            logger.exception("Failed to fetch tool list from data.gouv.fr MCP")
            raise

    async def handle_call(self, tool_name: str, args: dict[str, Any]) -> str | None:
        if tool_name not in self._cached_tool_names:
            return None
        return await self._call_tool(tool_name, args)

    async def _call_tool(self, name: str, args: dict[str, Any]) -> str:
        logger.info("data.gouv.fr MCP tool call — name={}", name)
        logger.debug("data.gouv.fr MCP tool args — name={}, args={}", name, args)
        try:
            async with streamable_http_client(self._url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, args)
                    response: str = result.content[0].text if result.content else ""  # type: ignore[union-attr]
                    logger.debug("data.gouv.fr MCP tool result (first 200 chars): {:.200}", response)
                    return response
        except Exception:
            logger.exception("data.gouv.fr MCP tool call failed — name={}", name)
            raise

    def _to_tool_definition(self, mcp_tool: Any) -> ToolDefinition:
        schema: dict[str, Any] = mcp_tool.inputSchema or {}
        raw_props: dict[str, Any] = schema.get("properties") or {}
        properties: dict[str, ToolParameter] = {
            k: ToolParameter(
                type=v.get("type", "string"),
                description=v.get("description", ""),
            )
            for k, v in raw_props.items()
        }
        return ToolDefinition(
            function=ToolFunction(
                name=mcp_tool.name,
                description=mcp_tool.description or "",
                parameters=ToolParameters(
                    properties=properties,
                    required=schema.get("required", []),
                ),
            )
        )
