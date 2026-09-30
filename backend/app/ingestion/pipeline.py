import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.cruise import Cruise
from app.db.models.document import Document
from app.db.session import SessionLocal
from app.ingestion.chunk import chunk_pages
from app.ingestion.embed import embed_document_chunks
from app.ingestion.extract import extract_pages
from app.ingestion.storage import download_pdf

NO_TEXT_MESSAGE = "No extractable text in PDF"
STUCK_PROCESSING = timedelta(minutes=10)


def run_ingest(document_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None or document.status != "processing":
            return
        cruise = db.get(Cruise, document.cruise_id)
        if cruise is None:
            _mark_failed(db, document, "Cruise not found")
            return

        pdf_bytes = download_pdf(document.storage_path)
        pages = extract_pages(pdf_bytes)
        if not any(page_text.strip() for _, page_text in pages):
            _mark_failed(db, document, NO_TEXT_MESSAGE)
            return

        chunked = chunk_pages(pages)
        if not chunked:
            _mark_failed(db, document, NO_TEXT_MESSAGE)
            return

        vectors = embed_document_chunks(chunked, cruise.name, cruise.year)

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
    except Exception as exc:
        db.rollback()
        document = db.get(Document, document_id)
        if document is not None:
            _mark_failed(db, document, str(exc))
    finally:
        db.close()


def can_retry(document: Document) -> bool:
    if document.status == "failed":
        return True
    if document.status != "processing":
        return False
    updated = document.updated_at
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - updated > STUCK_PROCESSING


def _mark_failed(db: Session, document: Document, message: str) -> None:
    document.status = "failed"
    document.error_message = message[:4000]
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
