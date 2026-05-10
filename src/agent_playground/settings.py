from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_playground.constants import PROJECT_ROOT


class AgentSettings(BaseSettings):
    """Pydantic class that represents the project settings.

    When an object of this class is created, it will read the environment variables.
    The pydantic settings library will read all the variables in .env and load it in
    the object AND in your environment variables.

    Warning: In `BaseSettings`, environment variables have precedence over variables
    defined in the `.env` file. If you modify values from the `.env` file, make sure
    to relaunch your shell or to source `.env`.
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_base_url: str = Field(..., description="Base URL for OpenAI-compatible API")
    openai_api_key: SecretStr = Field(..., description="API key for OpenAI-compatible API")
    model_name: str = Field(..., description="Model name to use for inference")
    tavily_api_key: SecretStr = Field(..., description="Tavily API key for web search")
    agent_host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    agent_port: int = Field(default=8000, description="Port to bind the server to")
