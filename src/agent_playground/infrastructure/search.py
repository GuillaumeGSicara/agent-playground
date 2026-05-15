from loguru import logger
from pydantic import SecretStr
from tavily import AsyncTavilyClient

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

    async def run(self, query: str) -> str:
        logger.info("Web search — query={!r}", query)
        response: dict = await self._client.search(query, max_results=5)
        results: list[dict] = response.get("results", [])
        logger.debug("Tavily returned {} result(s)", len(results))
        if not results:
            logger.info("No results for query {!r}", query)
            return f"No results found for '{query}'."
        lines: list[str] = []
        for r in results:
            lines.append(f"- {r['title']}\n  {r['url']}\n  {r['content']}")
        return "\n\n".join(lines)
