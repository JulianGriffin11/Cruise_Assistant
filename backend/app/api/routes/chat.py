import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.models.cruise import Cruise
from app.db.session import get_db
from app.setup.logging import log_event
from app.retrieval.chat_turn import chat_turn_events
from app.schemas.chat import ChatRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("")
def chat(body: ChatRequest, db: Session = Depends(get_db)) -> StreamingResponse:
    if body.cruise_id is not None and db.get(Cruise, body.cruise_id) is None:
        raise HTTPException(status_code=404, detail="Cruise not found")

    log_event(
        logger,
        logging.INFO,
        "chat_start",
        cruise_id=body.cruise_id,
        message_len=len(body.message),
        history_turns=len(body.history),
    )

    history = [{"role": turn.role, "content": turn.content} for turn in body.history]
    return StreamingResponse(
        chat_turn_events(
            db,
            body.message,
            body.cruise_id,
            history,
            len(body.history),
        ),
        media_type="text/event-stream",
    )
