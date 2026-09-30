"""Build embedding inputs for chunks (cruise name + year prefix) and call OpenAI."""

from app.embeddings import embed_texts


def embed_document_chunks(
    chunks: list[tuple[int, int, str]],
    cruise_name: str,
    cruise_year: int,
) -> list[list[float]]:
    inputs = [f"{cruise_name} {cruise_year}\n{text}" for _, _, text in chunks]
    return embed_texts(inputs)
