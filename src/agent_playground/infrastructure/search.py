from typing import Any

from loguru import logger
from pydantic import SecretStr
from tavily import AsyncTavilyClient
from tavily.errors import BadRequestError

from agent_playground.constants import ToolName
from agent_playground.models.tools import ToolDefinition, ToolFunction, ToolParameter, ToolParameters


class WebSearchTool:
    def __init__(self, api_key: SecretStr) -> None:
        self._client: AsyncTavilyClient = AsyncTavilyClient(api_key=api_key.get_secret_value())

    @property
    def name(self) -> str:
        return ToolName.WEB_SEARCH

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            function=ToolFunction(
                name=ToolName.WEB_SEARCH,
                description="Search the web for current information. Returns relevant results.",
                parameters=ToolParameters(
                    properties={"query": ToolParameter(type="string", description="The search query")},
                    required=["query"],
                ),
            )
        )

    async def list_definitions(self) -> list[ToolDefinition]:
        return [self.definition]

    async def handle_call(self, tool_name: str, args: dict[str, Any]) -> str | None:
        if tool_name != ToolName.WEB_SEARCH:
            return None
        return await self.run(args.get("query", ""))

    async def run(self, query: str) -> str:
        logger.info("Web search — query={!r}", query)
        try:
            response: dict[str, Any] = await self._client.search(query, max_results=5)
        except BadRequestError as e:
            logger.warning("Tavily bad request — query={!r}, error={}", query, e)
            return f"Search failed: {e}. Please reformulate the query with explicit search terms."
        results: list[dict[str, Any]] = response.get("results", [])
        logger.debug("Tavily returned {} result(s)", len(results))
        if not results:
            logger.info("No results for query {!r}", query)
            return f"No results found for '{query}'."
        lines: list[str] = []
        for r in results:
            lines.append(f"- {r['title']}\n  {r['url']}\n  {r['content']}")
        return "\n\n".join(lines)
