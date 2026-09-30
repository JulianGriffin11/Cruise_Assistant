"""Stream a grounded chat reply from retrieved chunks and citation metadata."""

import json
from collections.abc import Iterator

from openai import OpenAI

from app.config import get_settings
from app.retrieval.search import RetrievedChunk

CHAT_MODEL = "gpt-4o-mini"
REFUSAL_MESSAGE = (
    "The itinerary documents do not contain enough information to answer that question."
)

SYSTEM_PROMPT = """You answer questions using only the numbered source excerpts provided.
Quote dates and prices only when they appear in those excerpts; if they are not there, say the documents do not specify them.
If the excerpts do not support an answer, say so clearly instead of guessing.
When the user asks you to draft an email or letter, write it from the excerpts but do not put page numbers or citation markers inside the email body."""

HISTORY_LIMIT = 10


def stream_answer(
    message: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
) -> Iterator[str]:
    citations = _citations_from_chunks(chunks)
    if not chunks:
        yield _sse("token", REFUSAL_MESSAGE)
        yield _sse("citations", [])
        return

    client = OpenAI(api_key=get_settings().openai_api_key)
    messages = _build_messages(message, chunks, history)
    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
    )
    for event in stream:
        delta = event.choices[0].delta.content
        if delta:
            yield _sse("token", delta)
    yield _sse("citations", citations)


def _sse(event: str, data: str | list[dict[str, str | int]]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _citations_from_chunks(chunks: list[RetrievedChunk]) -> list[dict[str, str | int]]:
    seen: set[tuple[str, int, int]] = set()
    citations: list[dict[str, str | int]] = []
    for chunk in chunks:
        key = (chunk.cruise_name, chunk.cruise_year, chunk.page_number)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            {
                "cruise": chunk.cruise_name,
                "year": chunk.cruise_year,
                "page": chunk.page_number,
            }
        )
    citations.sort(key=lambda row: (row["cruise"], row["year"], row["page"]))
    return citations


def _build_messages(
    message: str,
    chunks: list[RetrievedChunk],
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[{index}] {chunk.cruise_name} {chunk.cruise_year}, page {chunk.page_number}\n"
            f"{chunk.text}"
        )
    system_content = SYSTEM_PROMPT + "\n\nSources:\n\n" + "\n\n".join(context_blocks)

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    for turn in history[-HISTORY_LIMIT:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})
    return messages
