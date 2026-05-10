from agent_playground.constants import ToolName
from agent_playground.models.tools import ToolDefinition, ToolFunction, ToolParameter, ToolParameters


class WebSearchTool:
    """Mock web search tool — real Tavily integration deferred."""

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
        return f"[MOCK] Web search for '{query}': No real results — Tavily integration pending."
