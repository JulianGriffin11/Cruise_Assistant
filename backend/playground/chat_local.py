"""Interactive chat in the terminal — same pipeline as POST /chat, no uvicorn.

Uses your .env (database + OpenAI). From backend/:

  uv run python playground/chat_local.py
  uv run python playground/chat_local.py --cruise-id <uuid>

Type a question and press Enter. /clear wipes thread memory; /quit exits.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlalchemy.orm import Session

from app.db.models.cruise import Cruise
from app.db.session import SessionLocal
from app.retrieval.answer import stream_answer
from app.retrieval.search import search_chunks


def _parse_sse(block: str) -> tuple[str | None, object | None]:
    event: str | None = None
    data: object | None = None
    for line in block.strip().splitlines():
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
        elif line.startswith("data:"):
            data = json.loads(line.removeprefix("data:").strip())
    return event, data


def _run_turn(
    db: Session,
    message: str,
    cruise_id: uuid.UUID | None,
    history: list[dict[str, str]],
) -> str:
    chunks = search_chunks(db, message, cruise_id)
    reply_parts: list[str] = []
    citations: list[dict[str, str | int]] = []

    print("\nAssistant: ", end="", flush=True)
    for block in stream_answer(message, chunks, history):
        event, data = _parse_sse(block)
        if event == "token" and isinstance(data, str):
            print(data, end="", flush=True)
            reply_parts.append(data)
        elif event == "citations" and isinstance(data, list):
            citations = data
    print()

    if citations:
        print("Sources:")
        for cite in citations:
            print(f"  • {cite['cruise']} ({cite['year']}), page {cite['page']}")
    print()

    return "".join(reply_parts)


def _resolve_cruise_id(db: Session, cruise_id: uuid.UUID | None) -> uuid.UUID | None:
    if cruise_id is not None:
        cruise = db.get(Cruise, cruise_id)
        if cruise is None:
            raise SystemExit(f"Cruise not found: {cruise_id}")
        print(f"Scope: {cruise.name} ({cruise.year})\n")
        return cruise_id

    cruises = db.query(Cruise).order_by(Cruise.year.desc(), Cruise.name).all()
    if not cruises:
        raise SystemExit("No cruises in the database. Create one and ingest a PDF first.")

    print("Cruise scope (Enter = search all ready documents):\n")
    for index, cruise in enumerate(cruises, start=1):
        print(f"  [{index}] {cruise.name} ({cruise.year})")
    print()

    choice = input("Pick a number or press Enter: ").strip()
    if not choice:
        print("Scope: all cruises\n")
        return None

    try:
        picked = cruises[int(choice) - 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit("Invalid selection.") from exc

    print(f"Scope: {picked.name} ({picked.year})\n")
    return picked.id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Terminal chat against ingested itineraries (no API server)."
    )
    parser.add_argument(
        "--cruise-id",
        type=uuid.UUID,
        help="Limit retrieval to this cruise (skip interactive picker)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        cruise_id = _resolve_cruise_id(db, args.cruise_id)
    finally:
        db.close()

    history: list[dict[str, str]] = []
    print("Ask about your itineraries. /clear = new thread, /quit = exit.\n")

    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not message:
            continue
        if message.lower() in {"/quit", "/exit", "/q"}:
            break
        if message.lower() == "/clear":
            history.clear()
            print("(thread cleared)\n")
            continue

        db = SessionLocal()
        try:
            reply = _run_turn(db, message, cruise_id, history)
        finally:
            db.close()

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
