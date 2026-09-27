from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.storage import ensure_itineraries_bucket


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_itineraries_bucket()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
