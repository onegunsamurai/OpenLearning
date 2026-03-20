from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    cors_origins: list[str] = ["http://localhost:3000"]
    langsmith_api_key: str = ""
    langsmith_project: str = "open-learning"
    langsmith_tracing: bool = False
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
