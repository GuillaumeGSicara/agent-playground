from enum import StrEnum
from pathlib import Path
from typing import Final


class AgentMeta(StrEnum):
    NAME = "Web Search Agent"
    DESCRIPTION = "An A2A and AG-UI compatible agent with web search capability"
    VERSION = "0.1.0"


class ToolName(StrEnum):
    WEB_SEARCH = "web_search"


class SkillId(StrEnum):
    WEB_SEARCH = "web_search"


PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent
"""The root directory of the project. This is used to construct absolute paths to files in the project, such as the .env file."""

PROMPTS_DIR: Final[Path] = Path(__file__).parent / "prompts"
"""The directory containing prompt .md files."""

MAX_REACT_ITERATIONS: Final[int] = 5
"""The maximum number of iterations the agent will perform in the ReAct loop."""
