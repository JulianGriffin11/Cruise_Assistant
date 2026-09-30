import uuid

import httpx

from app.config import get_settings

BUCKET = "itineraries"


def _headers() -> dict[str, str]:
    settings = get_settings()
    key = settings.supabase_service_role_key
    return {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }


def document_object_path(cruise_id: uuid.UUID, document_id: uuid.UUID) -> str:
    return f"{cruise_id}/{document_id}.pdf"


def ensure_itineraries_bucket() -> None:
    settings = get_settings()
    url = f"{settings.supabase_url}/storage/v1/bucket"
    with httpx.Client(timeout=30) as client:
        listed = client.get(url, headers=_headers())
        listed.raise_for_status()
        if any(bucket.get("id") == BUCKET or bucket.get("name") == BUCKET for bucket in listed.json()):
            return
        created = client.post(
            url,
            headers=_headers(),
            json={"id": BUCKET, "name": BUCKET, "public": False},
        )
        if created.status_code == 409:
            return
        created.raise_for_status()


def upload_pdf(storage_path: str, pdf_bytes: bytes) -> None:
    settings = get_settings()
    url = f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{storage_path}"
    headers = {
        **_headers(),
        "Content-Type": "application/pdf",
        "x-upsert": "true",
    }
    with httpx.Client(timeout=120) as client:
        response = client.post(url, headers=headers, content=pdf_bytes)
        response.raise_for_status()


def download_pdf(storage_path: str) -> bytes:
    settings = get_settings()
    url = f"{settings.supabase_url}/storage/v1/object/{BUCKET}/{storage_path}"
    with httpx.Client(timeout=120) as client:
        response = client.get(url, headers=_headers())
        response.raise_for_status()
        return response.content
