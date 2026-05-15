import uuid

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part
from loguru import logger

from agent_playground.models.events import TextChunkEvent
from agent_playground.services.agent import Agent


class WebSearchAgentExecutor(AgentExecutor):
    def __init__(self, agent: Agent) -> None:
        self._agent: Agent = agent

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id: str = context.task_id or ""
        context_id: str = context.context_id or ""
        logger.info("Task execute — task_id={}", task_id)
        updater: TaskUpdater = TaskUpdater(event_queue, task_id, context_id)
        await updater.start_work()

        artifact_id: str = str(uuid.uuid4())
        first_chunk: bool = True
        has_text: bool = False

        try:
            async for event in self._agent.run(context.get_user_input()):
                if isinstance(event, TextChunkEvent):
                    part: Part = Part()
                    part.text = event.delta
                    await updater.add_artifact(
                        parts=[part],
                        artifact_id=artifact_id,
                        append=not first_chunk,
                        last_chunk=False,
                    )
                    first_chunk = False
                    has_text = True

            if has_text:
                empty_part: Part = Part()
                empty_part.text = ""
                await updater.add_artifact(
                    parts=[empty_part],
                    artifact_id=artifact_id,
                    append=True,
                    last_chunk=True,
                )

            await updater.complete()
            logger.info("Task completed — task_id={}", task_id)
        except Exception as exc:
            logger.exception("Task failed — task_id={}", task_id)
            error_part: Part = Part()
            error_part.text = str(exc)
            await updater.failed(message=updater.new_agent_message(parts=[error_part]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id: str = context.task_id or ""
        context_id: str = context.context_id or ""
        logger.info("Task cancel — task_id={}", task_id)
        updater: TaskUpdater = TaskUpdater(event_queue, task_id, context_id)
        await updater.cancel()
