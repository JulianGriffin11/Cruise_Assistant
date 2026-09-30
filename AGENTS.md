# Agent Instructions

This file is the source of truth for any coding agent (Claude Code, Cursor, Codex, etc.) working in this repo. Read it before touching code.

## Stack

- **Backend:** Python + FastAPI
- **Frontend:** Vite + React SPA + TypeScript
- **Database:** Supabase Postgres (cruises, source documents, chunks)
- **Migrations:** SQLAlchemy models + Alembic from the backend
- **Retrieval:** Postgres full-text search on chunk text plus `pgvector` cosine search, combined into one ranked result set
- **Hosting:** Render (backend web service + frontend static site)
- **LLM + embeddings:** OpenAI

Stack is locked unless explicitly changed. Don't propose alternatives without a stated reason.

## Dependency policy

**Default: write it yourself. Reach for a library only when the alternative would be non-trivial, error-prone, or reinvention of a standard.** Every dependency is a liability — bundle size, supply-chain risk, future upgrade work.

OK to depend on:

- Things that are genuinely hard to get right (HTTP clients, ASGI servers, SQL drivers, parsers, LLM SDKs, ORM, migrations, auth SDKs).
- The declared stack (FastAPI, React, Vite, OpenAI SDK, etc.). Supabase Storage is accessed over HTTP with `httpx`, not a Supabase client package.

Not OK:

- Helper libraries that wrap 5–20 lines of stdlib or platform APIs.
- Frameworks where a function would do.
- "Nicer API" layers on top of an already-present dependency.

Before adding a runtime dep, answer in the commit message:

1. What exactly does it do that we can't write in <30 lines of clear code?
2. How often does it get used?
3. What's its maintenance / transitive-dep footprint?

## Configuration

A single settings module is the source of truth for environment per service (`backend/app/config.py`, `frontend/src/lib/env.ts`). Do not call `os.getenv`, read `process.env`, or read `import.meta.env` directly in app code outside those modules. Do not call `load_dotenv` anywhere except through the backend settings module's pydantic-settings config. If a third-party SDK reads env vars directly, mirror them in the settings module — don't sprinkle `setdefault` elsewhere.

Fail fast on startup if required config is missing. No silent fallbacks that hide real config errors.

## Backend layout

- **`app/ingestion/`** — ingest pipeline: Supabase Storage I/O for PDFs, PyMuPDF extract, chunking, embed inputs for chunks, `run_ingest`.
- **`app/retrieval/`** — ask pipeline: hybrid FTS + vector search, streaming answer + citations.
- **`app/embeddings/`** — shared OpenAI embedding calls (ingestion and retrieval both use this).
- **`app/api/routes/`** — thin HTTP handlers; call into ingestion or retrieval, do not embed pipeline logic in routes.

## Code style (universal)

- **Small, obvious functions.** A 15-line function with clear names beats a three-class abstraction.
- **No premature abstraction.** Three similar lines is better than a badly-named base class. Extract when there's a third caller, not a hypothetical one.
- **No error handling for cases that can't happen.** Trust internal callers and framework guarantees. Validate only at boundaries: HTTP input, external APIs, DB writes, untrusted parsing.
- **No backwards-compat shims** unless explicitly asked for.
- **No feature flags** added speculatively.
- **Comments:** explain *why* when non-obvious, never *what*. Remove stale TODOs.
- **Keep files focused.** Prefer small modules.
