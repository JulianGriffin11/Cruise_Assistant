import logging
import time
import uuid
from datetime import datetime, timedelta, timezone

from langfuse import observe
from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.cruise import Cruise
from app.db.models.document import Document
from app.db.session import SessionLocal
from app.ingestion.chunk import chunk_pages
from app.ingestion.embed import embed_document_chunks
from app.ingestion.extract import extract_pages
from app.ingestion.storage import download_pdf
from app.setup.langfuse import flush_langfuse
from app.setup.logging import log_event

logger = logging.getLogger(__name__)

NO_TEXT_MESSAGE = "No extractable text in PDF"
STUCK_PROCESSING = timedelta(minutes=10)


@observe(name="ingest-document")
def run_ingest(document_id: uuid.UUID) -> None:
    started = time.perf_counter()
    stage = "load"
    cruise_id: uuid.UUID | None = None
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or document.status != "processing":
            return
        cruise_id = document.cruise_id

        cruise = db.get(Cruise, document.cruise_id)
        if cruise is None:
            _mark_failed(db, document, "Cruise not found")
            _log_ingest_done(started, document_id, cruise_id, "failed", stage, "Cruise not found")
            return

        stage = "download"
        pdf_bytes = download_pdf(document.storage_path)
        stage = "extract"
        pages = extract_pages(pdf_bytes)
        if not any(page_text.strip() for _, page_text in pages):
            _mark_failed(db, document, NO_TEXT_MESSAGE)
            _log_ingest_done(started, document_id, cruise_id, "failed", stage, NO_TEXT_MESSAGE)
            return

        chunked = chunk_pages(pages)
        if not chunked:
            _mark_failed(db, document, NO_TEXT_MESSAGE)
            _log_ingest_done(started, document_id, cruise_id, "failed", stage, NO_TEXT_MESSAGE)
            return

        stage = "embed"
        vectors = embed_document_chunks(chunked, cruise.name, cruise.year)

        stage = "persist"
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        for (page_number, chunk_index, text), embedding in zip(
            chunked, vectors, strict=True
        ):
            db.add(
                Chunk(
                    document_id=document.id,
                    cruise_id=document.cruise_id,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=text,
                    embedding=embedding,
                )
            )
        document.page_count = len(pages)
        document.status = "ready"
        document.error_message = None
        document.updated_at = datetime.now(timezone.utc)
        db.commit()
        _log_ingest_done(
            started,
            document_id,
            cruise_id,
            "ready",
            page_count=len(pages),
            chunk_count=len(chunked),
        )
    except Exception as exc:
        db.rollback()
        failed_doc = db.get(Document, document_id)
        if failed_doc is not None:
            cruise_id = failed_doc.cruise_id
            _mark_failed(db, failed_doc, str(exc))
        _log_ingest_done(started, document_id, cruise_id, "failed", stage, str(exc))
    finally:
        db.close()
        flush_langfuse()


def can_retry(document: Document) -> bool:
    if document.status == "failed":
        return True
    if document.status != "processing":
        return False
    updated = document.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - updated > STUCK_PROCESSING


def _log_ingest_done(
    started: float,
    document_id: uuid.UUID,
    cruise_id: uuid.UUID | None,
    status: str,
    stage: str | None = None,
    error: str | None = None,
    page_count: int | None = None,
    chunk_count: int | None = None,
) -> None:
    fields: dict[str, object] = {
        "document_id": document_id,
        "cruise_id": cruise_id,
        "status": status,
        "duration_ms": round((time.perf_counter() - started) * 1000),
    }
    if page_count is not None:
        fields["page_count"] = page_count
    if chunk_count is not None:
        fields["chunk_count"] = chunk_count
    if stage is not None:
        fields["stage"] = stage
    if error is not None:
        fields["error"] = error[:500]
    level = logging.ERROR if status == "failed" else logging.INFO
    log_event(logger, level, "ingest_done", **fields)


def _mark_failed(db: Session, document: Document, message: str) -> None:
    document.status = "failed"
    document.error_message = message[:4000]
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
