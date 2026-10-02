from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    openai_api_key: str
    cors_origins: list[str]

    # Retrieval & LLM
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"
    chat_history_limit: int = 10
    retrieval_rrf_k: int = 60
    retrieval_candidate_limit: int = 20
    retrieval_result_limit: int = 5
    retrieval_weak_cosine_distance: float = 0.55

    # Logging
    log_level: str = "INFO"
    log_json: bool = False

    # Langfuse
    langfuse_public_key: str
    langfuse_secret_key: str
    langfuse_base_url: str
    langfuse_enabled: bool = True

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, level: str) -> str:
        normalized = level.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"log_level must be one of {sorted(allowed)}")
        return normalized

    @field_validator("database_url")
    @classmethod
    def direct_database_url(cls, url: str) -> str:
        if urlparse(url).port == 6543:
            raise ValueError(
                "DATABASE_URL must be the direct Supabase connection on port 5432, "
                "not the transaction pooler on 6543"
            )
        if url.startswith("postgres://"):
            url = "postgresql://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url

    @field_validator("supabase_url")
    @classmethod
    def strip_supabase_url(cls, url: str) -> str:
        return url.rstrip("/")

    @field_validator("cors_origins")
    @classmethod
    def strip_cors_origins(cls, origins: list[str]) -> list[str]:
        return [origin.rstrip("/") for origin in origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()
