from enum import StrEnum
from pathlib import Path
from typing import Final


class AgentMeta(StrEnum):
    NAME = "Open Data Agent"
    DESCRIPTION = "An A2A and AG-UI compatible agent with web search and data.gouv.fr open data access"
    VERSION = "0.1.0"


class ToolName(StrEnum):
    WEB_SEARCH = "web_search"


class SkillId(StrEnum):
    WEB_SEARCH = "web_search"


PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent
"""Root directory of the project; used to locate the .env file and other project-level resources."""

PROMPTS_DIR: Final[Path] = Path(__file__).parent / "prompts"
"""The directory containing prompt .md files."""

MAX_REACT_ITERATIONS: Final[int] = 5
"""The maximum number of iterations the agent will perform in the ReAct loop."""

DATAGOUV_MCP_URL: Final[str] = "https://mcp.data.gouv.fr/mcp"
"""The URL of the data.gouv.fr MCP server (streamable HTTP transport)."""
