import httpx

from app.config import get_settings

BUCKET = "itineraries"


def ensure_itineraries_bucket() -> None:
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key,
    }
    url = f"{settings.supabase_url}/storage/v1/bucket"
    with httpx.Client(timeout=30) as client:
        listed = client.get(url, headers=headers)
        listed.raise_for_status()
        if any(bucket.get("id") == BUCKET or bucket.get("name") == BUCKET for bucket in listed.json()):
            return
        created = client.post(
            url,
            headers=headers,
            json={"id": BUCKET, "name": BUCKET, "public": False},
        )
        if created.status_code == 409:
            return
        created.raise_for_status()
