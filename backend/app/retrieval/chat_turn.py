import uuid
from collections.abc import Iterator

from langfuse import get_client, observe
from sqlalchemy.orm import Session

from app.retrieval.answer import stream_answer
from app.retrieval.search import search_chunks


@observe(name="chat-turn", capture_input=False)
def chat_turn_events(
    db: Session,
    message: str,
    cruise_id: uuid.UUID | None,
    history: list[dict[str, str]],
    history_turns: int,
) -> Iterator[str]:
    get_client().update_current_span(
        input={
            "message": message,
            "cruise_id": str(cruise_id) if cruise_id else None,
            "history_turns": history_turns,
        }
    )
    chunks = search_chunks(db, message, cruise_id)
    yield from stream_answer(message, chunks, history)
