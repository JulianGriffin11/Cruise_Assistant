from langfuse import Langfuse, get_client

from app.setup.config import Settings


def configure_langfuse(settings: Settings) -> None:
    Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_base_url.rstrip("/"),
        tracing_enabled=settings.langfuse_enabled,
    )


def flush_langfuse() -> None:
    get_client().flush()
