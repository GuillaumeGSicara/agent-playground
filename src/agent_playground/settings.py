from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_playground.constants import PROJECT_ROOT


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_base_url: str = Field(..., description="Base URL for OpenAI-compatible API")
    openai_api_key: SecretStr = Field(..., description="API key for OpenAI-compatible API")
    model_name: str = Field(..., description="Model name to use for inference")
    tavily_api_key: SecretStr | None = Field(default=None, description="Tavily API key (real search, deferred)")
    agent_host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    agent_port: int = Field(default=8000, description="Port to bind the server to")
