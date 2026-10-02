"""Hybrid full-text + pgvector search over ready documents."""

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.setup.config import get_settings
from app.db.models.chunk import Chunk
from app.db.models.cruise import Cruise
from app.db.models.document import Document
from app.embeddings import embed_texts
from app.setup.logging import log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: uuid.UUID
    text: str
    page_number: int
    cruise_name: str
    cruise_year: int


def search_chunks(
    db: Session,
    query: str,
    cruise_id: uuid.UUID | None,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    settings = get_settings()
    if limit is None:
        limit = settings.retrieval_result_limit

    started = time.perf_counter()
    embed_input = query
    if cruise_id is not None:
        cruise = db.get(Cruise, cruise_id)
        if cruise is not None:
            embed_input = f"{cruise.name} {cruise.year}\n{query}"

    query_vector = embed_texts([embed_input])[0]
    ts_query = func.plainto_tsquery("english", query)

    fts_rows = db.execute(
        _ready_chunk_select(cruise_id)
        .where(Chunk.text_search.op("@@")(ts_query))
        .order_by(func.ts_rank_cd(Chunk.text_search, ts_query).desc())
        .limit(settings.retrieval_candidate_limit)
    ).all()

    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")
    vector_rows = db.execute(
        _ready_chunk_select(cruise_id, extra_columns=(distance,))
        .order_by(distance)
        .limit(settings.retrieval_candidate_limit)
    ).all()

    fts_hits = [_row_to_chunk(row) for row in fts_rows]
    fts_ids = {chunk.chunk_id for chunk in fts_hits}

    vector_hits: list[tuple[RetrievedChunk, float]] = []
    for row in vector_rows:
        chunk = _row_to_chunk(row)
        dist = float(row[-1])
        vector_hits.append((chunk, dist))

    vector_by_id = {chunk.chunk_id: dist for chunk, dist in vector_hits}
    chunk_by_id: dict[uuid.UUID, RetrievedChunk] = {}
    scores: dict[uuid.UUID, float] = {}

    for rank, chunk in enumerate(fts_hits, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (
            settings.retrieval_rrf_k + rank
        )
        chunk_by_id[chunk.chunk_id] = chunk

    for rank, (chunk, _dist) in enumerate(vector_hits, start=1):
        scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (
            settings.retrieval_rrf_k + rank
        )
        chunk_by_id.setdefault(chunk.chunk_id, chunk)

    ranked_ids = sorted(scores.keys(), key=lambda cid: scores[cid], reverse=True)
    results: list[RetrievedChunk] = []
    filtered_weak = 0
    for chunk_id in ranked_ids:
        dist = vector_by_id.get(chunk_id)
        in_fts = chunk_id in fts_ids
        if (
            dist is not None
            and dist > settings.retrieval_weak_cosine_distance
            and not in_fts
        ):
            filtered_weak += 1
            continue
        results.append(chunk_by_id[chunk_id])
        if len(results) >= limit:
            break

    duration_ms = round((time.perf_counter() - started) * 1000)
    summary_fields = {
        "cruise_id": cruise_id,
        "fts_count": len(fts_hits),
        "vector_count": len(vector_hits),
        "filtered_weak": filtered_weak,
        "result_count": len(results),
        "duration_ms": duration_ms,
    }
    level = logging.WARNING if not results else logging.INFO
    log_event(logger, level, "retrieval_summary", **summary_fields)

    if logger.isEnabledFor(logging.DEBUG):
        chunk_ids = [str(chunk.chunk_id) for chunk in results]
        distances = [vector_by_id[c.chunk_id] for c in results if c.chunk_id in vector_by_id]
        detail: dict[str, object] = {"chunk_ids": chunk_ids}
        if distances:
            detail["vector_distance_min"] = min(distances)
            detail["vector_distance_max"] = max(distances)
        log_event(logger, logging.DEBUG, "retrieval_detail", **detail)

    return results


def _ready_chunk_select(cruise_id: uuid.UUID | None, extra_columns=()):
    columns = (Chunk, Cruise.name, Cruise.year, *extra_columns)
    stmt = (
        select(*columns)
        .join(Document, Chunk.document_id == Document.id)
        .join(Cruise, Chunk.cruise_id == Cruise.id)
        .where(Document.status == "ready")
    )
    if cruise_id is not None:
        stmt = stmt.where(Chunk.cruise_id == cruise_id)
    return stmt


def _row_to_chunk(row) -> RetrievedChunk:
    chunk, cruise_name, cruise_year = row[0], row[1], row[2]
    return RetrievedChunk(
        chunk_id=chunk.id,
        text=chunk.text,
        page_number=chunk.page_number,
        cruise_name=cruise_name,
        cruise_year=cruise_year,
    )
