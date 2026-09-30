import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models.cruise import Cruise
from app.db.models.document import Document
from app.db.session import get_db
from app.ingestion.pipeline import can_retry, run_ingest
from app.ingestion.storage import document_object_path, upload_pdf
from app.schemas.document import DocumentRead

router = APIRouter()

MAX_UPLOAD_BYTES = 32 * 1024 * 1024


@router.get("", response_model=list[DocumentRead])
def list_documents(
    cruise_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[Document]:
    query = db.query(Document).order_by(Document.updated_at.desc())
    if cruise_id is not None:
        query = query.filter(Document.cruise_id == cruise_id)
    return query.all()


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: uuid.UUID, db: Session = Depends(get_db)) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    cruise_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    cruise = db.get(Cruise, cruise_id)
    if cruise is None:
        raise HTTPException(status_code=404, detail="Cruise not found")

    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds 32MB limit")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    document_id = uuid.uuid4()
    storage_path = document_object_path(cruise_id, document_id)
    upload_pdf(storage_path, pdf_bytes)

    now = datetime.now(timezone.utc)
    document = Document(
        id=document_id,
        cruise_id=cruise_id,
        filename=filename,
        storage_path=storage_path,
        page_count=None,
        status="processing",
        error_message=None,
        updated_at=now,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(run_ingest, document.id)
    return document


@router.post("/{document_id}/retry", response_model=DocumentRead)
def retry_document(
    document_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Document:
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if not can_retry(document):
        raise HTTPException(status_code=409, detail="Document is not eligible for retry")

    document.status = "processing"
    document.error_message = None
    document.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(run_ingest, document.id)
    return document
