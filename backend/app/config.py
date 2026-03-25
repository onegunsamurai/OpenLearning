import os
from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    langsmith_api_key: str = ""
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_project: str = "open-learning"
    langsmith_tracing: bool = False
    langsmith_workspace_id: str = ""
    database_url: str = "postgresql+asyncpg://openlearning:openlearning@localhost:5432/openlearning"
    github_client_id: str = ""
    github_client_secret: str = ""
    jwt_secret_key: str = ""
    encryption_key: str = ""
    frontend_url: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def configure_langsmith_tracing() -> None:
    """Bridge LangSmith settings from pydantic-settings into os.environ.

    The LangSmith SDK reads tracing config directly from os.environ,
    but pydantic-settings only loads .env values into the Settings object.
    Uses setdefault so explicit shell exports take precedence.
    """
    s = get_settings()
    if not s.langsmith_tracing:
        return
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    if s.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", s.langsmith_api_key)
    if s.langsmith_endpoint:
        os.environ.setdefault("LANGSMITH_ENDPOINT", s.langsmith_endpoint)
    if s.langsmith_project:
        os.environ.setdefault("LANGSMITH_PROJECT", s.langsmith_project)
    if s.langsmith_workspace_id:
        os.environ.setdefault("LANGSMITH_WORKSPACE_ID", s.langsmith_workspace_id)
