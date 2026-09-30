"""Stream a grounded chat reply from retrieved chunks and citation metadata."""

from typing import Any


async def stream_answer(
    query: str,
    chunks: list[Any],
    history: list[dict[str, str]],
):
    raise NotImplementedError
