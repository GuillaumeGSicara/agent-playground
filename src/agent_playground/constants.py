from enum import StrEnum
from pathlib import Path


class AgentMeta(StrEnum):
    NAME = "Web Search Agent"
    DESCRIPTION = "An A2A and AG-UI compatible agent with web search capability"
    VERSION = "0.1.0"


class ToolName(StrEnum):
    WEB_SEARCH = "web_search"


class SkillId(StrEnum):
    WEB_SEARCH = "web_search"


PROJECT_ROOT: Path = Path(__file__).parent.parent.parent

SYSTEM_PROMPT: str = (
    "You are a helpful assistant with access to web search. Use the web_search tool when you need current information."
)

MAX_REACT_ITERATIONS: int = 5
