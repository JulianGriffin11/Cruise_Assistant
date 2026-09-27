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


@lru_cache
def get_settings() -> Settings:
    return Settings()
