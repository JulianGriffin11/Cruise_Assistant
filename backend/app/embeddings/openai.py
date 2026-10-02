import logging
import time

from langfuse.openai import OpenAI

from app.setup.config import get_settings
from app.setup.logging import log_event

logger = logging.getLogger(__name__)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    started = time.perf_counter()
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.embeddings.create(model=settings.embedding_model, input=texts)
    ordered = sorted(response.data, key=lambda row: row.index)
    log_event(
        logger,
        logging.INFO,
        "embed_batch",
        text_count=len(texts),
        duration_ms=round((time.perf_counter() - started) * 1000),
    )
    return [row.embedding for row in ordered]
