from loguru import logger
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import AgentCard

from agent_playground.services.agui import AguiHandler
from agent_playground.services.executor import WebSearchAgentExecutor


def build_app(
    agent_card: AgentCard,
    executor: WebSearchAgentExecutor,
    agui_handler: AguiHandler,
) -> Starlette:
    request_handler: DefaultRequestHandler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    async def ping(_request: Request) -> JSONResponse:
        logger.debug("GET /ping")
        return JSONResponse({"status": "Healthy"})

    all_routes: list[Route] = [
        *create_agent_card_routes(agent_card),
        *create_jsonrpc_routes(request_handler, rpc_url="/"),
        Route("/invocations", agui_handler.handle, methods=["POST"]),
        Route("/ping", ping, methods=["GET"]),
    ]

    return Starlette(routes=all_routes)
