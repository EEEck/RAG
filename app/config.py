from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str | None = None
    openai_base_url: str | None = None

    # Legacy/Default (falls back to single DB if specific ones not set)
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_user: str = "rag"
    postgres_password: str = "rag"
    postgres_db: str = "rag"

    # Content DB Config
    postgres_content_host: str | None = None
    postgres_content_port: int = 5432
    postgres_content_user: str | None = None
    postgres_content_password: str | None = None
    postgres_content_db: str | None = None

    # User DB Config
    postgres_user_host: str | None = None
    postgres_user_port: int = 5432
    postgres_user_user: str | None = None
    postgres_user_password: str | None = None
    postgres_user_db: str | None = None

    embed_model: str = "text-embedding-3-large"
    chat_model: str = "gpt-4.1-mini"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

    @property
    def pg_content_dsn(self) -> str:
        host = self.postgres_content_host or self.postgres_host
        port = self.postgres_content_port or self.postgres_port
        user = self.postgres_content_user or self.postgres_user
        password = self.postgres_content_password or self.postgres_password
        db = self.postgres_content_db or self.postgres_db
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    @property
    def pg_user_dsn(self) -> str:
        host = self.postgres_user_host or self.postgres_host
        port = self.postgres_user_port or self.postgres_port
        user = self.postgres_user_user or self.postgres_user
        password = self.postgres_user_password or self.postgres_password
        db = self.postgres_user_db or self.postgres_db
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
