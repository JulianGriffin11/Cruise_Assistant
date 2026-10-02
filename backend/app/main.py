import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.ingestion.storage import ensure_itineraries_bucket
from app.setup.config import get_settings
from app.setup.langfuse import configure_langfuse, flush_langfuse
from app.setup.logging import configure_logging, reset_request_id, set_request_id

_settings = get_settings()
configure_logging(_settings)
configure_langfuse(_settings)

from app.api.routes import chat, cruises, documents  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_itineraries_bucket()
    try:
        yield
    finally:
        flush_langfuse()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cruises.router, prefix="/cruises", tags=["cruises"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    if request.url.path == "/health":
        return await call_next(request)

    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    token = set_request_id(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        reset_request_id(token)


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}


# Present after scripts/render-build.sh. Local API runs stay API-only without it.
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def _mount_frontend(dist: Path) -> None:
    """Serve the Vite build from the same origin as the API."""
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/", include_in_schema=False)
    def spa_index() -> FileResponse:
        return FileResponse(dist / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str) -> FileResponse:
        candidate = (dist / full_path).resolve()
        if candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


if _DIST.is_dir():
    _mount_frontend(_DIST)
