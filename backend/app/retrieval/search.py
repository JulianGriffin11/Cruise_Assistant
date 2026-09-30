"""Hybrid full-text + pgvector search over ready documents."""

import uuid
from typing import Any

from sqlalchemy.orm import Session


def search_chunks(
    db: Session,
    query: str,
    cruise_id: uuid.UUID | None,
    limit: int = 8,
) -> list[Any]:
    raise NotImplementedError
