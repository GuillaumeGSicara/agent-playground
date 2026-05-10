import uvicorn

from agent_playground.card import build_agent_card
from agent_playground.execution.agui import AguiHandler
from agent_playground.execution.agent import Agent
from agent_playground.execution.executor import WebSearchAgentExecutor
from agent_playground.infrastructure.llm import LLMClient
from agent_playground.infrastructure.search import WebSearchTool
from agent_playground.server.app import build_app
from agent_playground.settings import AgentSettings


def main() -> None:
    settings: AgentSettings = AgentSettings()  # type: ignore[call-arg]

    llm_client: LLMClient = LLMClient(
        base_url=settings.openai_api_base_url,
        api_key=settings.openai_api_key,
        model_name=settings.model_name,
    )
    search_tool: WebSearchTool = WebSearchTool()
    agent: Agent = Agent(llm_client=llm_client, search_tool=search_tool)
    executor: WebSearchAgentExecutor = WebSearchAgentExecutor(agent=agent)
    agui_handler: AguiHandler = AguiHandler(agent=agent)

    agent_card = build_agent_card(url=f"http://{settings.agent_host}:{settings.agent_port}")
    app = build_app(agent_card=agent_card, executor=executor, agui_handler=agui_handler)

    uvicorn.run(app, host=settings.agent_host, port=settings.agent_port)


if __name__ == "__main__":
    main()
