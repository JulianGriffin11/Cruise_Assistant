from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import chat, cruises, documents
from app.db.session import get_db
from app.ingestion.storage import ensure_itineraries_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_itineraries_bucket()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(cruises.router, prefix="/cruises", tags=["cruises"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
