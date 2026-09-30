"""Run the full ingest pipeline on a PDF from repo Data/ (no API server).

From backend/ with .env configured:

  uv run python playground/ingest_local.py
  uv run python playground/ingest_local.py ../Data/my-trip.pdf
  uv run python playground/ingest_local.py --cruise-name "Alaska 2026" --cruise-year 2026
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

LOCAL_DATA_DIR = _BACKEND_ROOT.parent / "data"
MAX_UPLOAD_BYTES = 32 * 1024 * 1024

from sqlalchemy.orm import Session

from app.db.models.chunk import Chunk
from app.db.models.cruise import Cruise
from app.db.models.document import Document
from app.db.session import SessionLocal
from app.ingestion.pipeline import run_ingest
from app.ingestion.storage import (
    document_object_path,
    ensure_itineraries_bucket,
    upload_pdf,
)


def _resolve_pdf(path: Path | None) -> Path:
    if path is not None:
        pdf = path.expanduser().resolve()
        if not pdf.is_file():
            raise SystemExit(f"File not found: {pdf}")
        return pdf

    if not LOCAL_DATA_DIR.is_dir():
        raise SystemExit(
            f"Data folder missing: {LOCAL_DATA_DIR}\n"
            "Create it and drop a PDF there, or pass a path argument."
        )
    pdfs = sorted(LOCAL_DATA_DIR.glob("*.pdf"))
    if not pdfs:
        raise SystemExit(
            f"No PDFs in {LOCAL_DATA_DIR}\n"
            "Add a .pdf file and run again, or pass a path argument."
        )
    if len(pdfs) > 1:
        names = "\n  ".join(p.name for p in pdfs)
        raise SystemExit(
            f"Multiple PDFs in {LOCAL_DATA_DIR}; pass which one to use:\n  {names}"
        )
    return pdfs[0]


def _load_pdf(pdf_path: Path) -> tuple[str, bytes]:
    pdf_bytes = pdf_path.read_bytes()
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise SystemExit(f"PDF exceeds 32MB limit: {pdf_path}")
    if not pdf_bytes.startswith(b"%PDF"):
        raise SystemExit(f"Not a PDF (missing %PDF header): {pdf_path}")
    return pdf_path.name, pdf_bytes


def _get_or_create_cruise(
    db: Session,
    cruise_id: uuid.UUID | None,
    cruise_name: str,
    cruise_year: int,
) -> Cruise:
    if cruise_id is not None:
        cruise = db.get(Cruise, cruise_id)
        if cruise is None:
            raise SystemExit(f"Cruise not found: {cruise_id}")
        return cruise

    cruise = Cruise(name=cruise_name, year=cruise_year)
    db.add(cruise)
    db.commit()
    db.refresh(cruise)
    return cruise


def _create_document_and_upload(
    db: Session,
    cruise_id: uuid.UUID,
    filename: str,
    pdf_bytes: bytes,
) -> Document:
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
    return document


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a local PDF through Storage + run_ingest."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        type=Path,
        help=f"Path to PDF (default: sole *.pdf in {LOCAL_DATA_DIR})",
    )
    parser.add_argument(
        "--cruise-id",
        type=uuid.UUID,
        help="Use an existing cruise instead of creating one",
    )
    parser.add_argument(
        "--cruise-name", default="Local test cruise", help="Name when creating a cruise"
    )
    parser.add_argument(
        "--cruise-year",
        type=int,
        default=datetime.now().year,
        help="Year when creating a cruise",
    )
    args = parser.parse_args()

    pdf_path = _resolve_pdf(args.pdf)
    filename, pdf_bytes = _load_pdf(pdf_path)

    print(f"PDF: {pdf_path}")
    ensure_itineraries_bucket()

    db = SessionLocal()
    try:
        cruise = _get_or_create_cruise(
            db, args.cruise_id, args.cruise_name, args.cruise_year
        )
        document = _create_document_and_upload(db, cruise.id, filename, pdf_bytes)
        document_id = document.id
        print(f"Cruise: {cruise.name} ({cruise.year}) id={cruise.id}")
        print(f"Document id={document_id} status=processing — running ingest…")
    finally:
        db.close()

    run_ingest(document_id)

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            raise SystemExit("Document row missing after ingest.")
        chunk_count = db.query(Chunk).filter(Chunk.document_id == document_id).count()
        print(f"Status: {document.status}")
        if document.error_message:
            print(f"Error: {document.error_message}")
        if document.status == "ready":
            print(f"Pages: {document.page_count}  Chunks: {chunk_count}")
        if document.status != "ready":
            sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
