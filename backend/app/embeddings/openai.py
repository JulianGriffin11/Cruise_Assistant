from openai import OpenAI

from app.config import get_settings

EMBEDDING_MODEL = "text-embedding-3-small"


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = OpenAI(api_key=get_settings().openai_api_key)
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    ordered = sorted(response.data, key=lambda row: row.index)
    return [row.embedding for row in ordered]
