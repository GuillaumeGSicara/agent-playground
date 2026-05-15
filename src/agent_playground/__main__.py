import uvicorn
from loguru import logger
from starlette.applications import Starlette

from a2a.types import AgentCard

from agent_playground.configuration import configure_logging
from agent_playground.infrastructure.llm import LLMClient
from agent_playground.infrastructure.search import WebSearchTool
from agent_playground.server.app import build_app
from agent_playground.server.card import build_agent_card
from agent_playground.services.agent import Agent
from agent_playground.services.agui import AguiHandler
from agent_playground.services.executor import WebSearchAgentExecutor
from agent_playground.settings import AgentSettings


def main() -> None:
    settings: AgentSettings = AgentSettings()  # type: ignore[call-arg]
    configure_logging(settings.log_level)

    logger.info(
        "agent-playground starting — model={}, {}:{}",
        settings.model_name,
        settings.agent_host,
        settings.agent_port,
    )
    logger.debug("LLM base URL: {}", settings.openai_api_base_url)

    llm_client: LLMClient = LLMClient(
        base_url=settings.openai_api_base_url,
        api_key=settings.openai_api_key,
        model_name=settings.model_name,
    )
    search_tool: WebSearchTool = WebSearchTool(api_key=settings.tavily_api_key)
    agent: Agent = Agent(llm_client=llm_client, search_tool=search_tool)
    executor: WebSearchAgentExecutor = WebSearchAgentExecutor(agent=agent)
    agui_handler: AguiHandler = AguiHandler(agent=agent)

    agent_card: AgentCard = build_agent_card(url=f"http://{settings.agent_host}:{settings.agent_port}")
    app: Starlette = build_app(
        agent_card=agent_card,
        executor=executor,
        agui_handler=agui_handler,
    )

    logger.info("Listening on http://{}:{}", settings.agent_host, settings.agent_port)
    uvicorn.run(app, host=settings.agent_host, port=settings.agent_port, log_config=None)


if __name__ == "__main__":
    main()
