from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.models.cruise import Cruise
from app.db.session import get_db
from app.retrieval.answer import stream_answer
from app.retrieval.search import search_chunks
from app.schemas.chat import ChatRequest

router = APIRouter()


@router.post("")
def chat(body: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    if body.cruise_id is not None and db.get(Cruise, body.cruise_id) is None:
        raise HTTPException(status_code=404, detail="Cruise not found")

    chunks = search_chunks(db, body.message, body.cruise_id)
    history = [{"role": turn.role, "content": turn.content} for turn in body.history]
    return StreamingResponse(
        stream_answer(body.message, chunks, history),
        media_type="text/event-stream",
    )
