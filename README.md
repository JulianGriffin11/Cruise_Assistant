# Cruise Assistant

Internal tool for a cruise operator. Upload a package itinerary PDF (about 20 pages, a few per year), then ask questions grounded in those docs. Answers cite the cruise and the page. The open chat thread stays in the browser and clears on refresh.

Check a box when that step is done.

## Backend layout

HTTP routes live under `backend/app/api/routes/`. Pipelines live under `backend/app/`:

- **`ingestion/`** — upload storage, PDF extract, chunking, document embeddings, and `run_ingest` (background job).
- **`retrieval/`** — hybrid search over chunks and streaming grounded answers (Phase 4).
- **`embeddings/`** — shared OpenAI `text-embedding-3-small` helper used by both pipelines.

## Phase 1 — Skeleton

- [x] Python project with FastAPI, settings, and a SQLAlchemy session
- [x] Alembic set up against the direct Supabase database URL (port 5432)
- [x] Supabase Postgres with the `vector` extension
- [x] Supabase Storage bucket `itineraries` for the original PDFs
- [x] Health check that confirms the API can reach the database

## Phase 2 — Data model

- [x] `cruises` table: name, year, optional start and end dates
- [x] `documents` table: cruise, filename, storage path, page count, status, error message
- [x] `chunks` table: document, cruise, page number, chunk index, text, embedding `vector(1536)`
- [x] Migration adds the cruise, document, and chunk tables
- [x] No conversation or message tables in this version

## Phase 3 — Ingest

- [x] `POST /documents` accepts a PDF, stores it, and returns while status is `processing`
- [x] Background ingest extracts text per page with PyMuPDF
- [x] Empty text marks the document `failed` (scanned PDFs are out of scope)
- [x] Chunk by page, about 500–800 tokens, with overlap and the page number kept
- [x] Embed chunks with `text-embedding-3-small` and insert them
- [x] Status ends as `ready` or `failed`, with `GET /documents/{id}` for the UI to poll
- [x] `POST /documents/{id}/retry` re-runs a failed ingest

## Phase 4 — Ask

- [x] `POST /chat` accepts the question, an optional cruise, and the recent turns already on screen
- [x] Hybrid search: Postgres full-text on chunk text plus cosine distance on the question embedding, merge into one ranked set, take the top 8
- [x] Drop weak matches, and filter by cruise when one is selected
- [x] Stream a grounded answer, then send citations (cruise name and page)
- [x] Prompt quotes dates and prices only when the chunks contain them, and says when the docs do not
- [x] A request to draft an email is the same chat call; page citations stay under the reply, not inside the letter
- [x] Nothing about the thread is written to the database

## Phase 5 — Frontend

- [x] Vite, React, TypeScript, and Tailwind
- [x] shadcn/ui init, with button, input, textarea, card, select, badge, dialog, scroll-area, separator, alert, and skeleton
- [x] Library page: cruise cards, dialog to create a cruise, PDF upload
- [x] Library page: status badge and skeleton while a document is processing
- [x] Chat page: cruise select (or search all), scroll area, textarea, and send button
- [x] Chat page: stream the reply and show cruise name and page under each answer
- [x] Thread lives in React state and clears on refresh

## Phase 6 — Check the path

- [x] Upload one real itinerary and wait until it is `ready`
- [x] Ask a question whose answer is on a known page and confirm that page is cited
- [x] Ask a question the PDF does not answer and confirm it does not invent details

## Phase 7 — Deploy (Render)

Blueprint: [render.yaml](render.yaml) defines one web service. FastAPI serves the API and the built frontend on the same URL.

| Service | URL |
|---------|-----|
| `cruise-assistant` | `https://cruise-assistant.onrender.com` |

Leave **Root Directory** empty. Runtime is **Python**. Commands:

| Field | Command |
|---------|---------|
| Build | `./scripts/render-build.sh` |
| Start | `./scripts/start.sh` |

Leave **Pre-Deploy** empty. Render only allows that command on paid web services. `scripts/start.sh` runs `alembic upgrade head` before uvicorn.

The build installs Node dependencies, builds `frontend/dist`, and installs the Python app with `uv`. Start serves that build and the API from one process. The production frontend calls `/cruises`, `/documents`, and `/chat` on this same host, so `VITE_API_BASE_URL` stays unset.

### One-time setup

1. Push the branch Render builds (includes `render.yaml` and `scripts/`).
2. In [Render](https://dashboard.render.com): **New** → **Blueprint** → connect `JulianGriffin11/Cruise_Assistant`. Or create one **Web Service**, runtime **Python**, and set the commands above.
3. Set secret env vars (same values as local `backend/.env`):
   - `DATABASE_URL` — Supabase **direct** URL, port **5432** (not the 6543 pooler)
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`
   - `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`
4. Deploy. Health check path is `/health`.

### Verify

- `GET https://cruise-assistant.onrender.com/health` → `{"status":"ok"}`
- Open `https://cruise-assistant.onrender.com` (Library loads cruises from Supabase).

### Production smoke test (browser, not localhost)

1. Upload a PDF → wait until status **ready**.
2. Ask a question with a known answer → confirm cruise + page citation.
3. Ask something not in the PDF → confirm refusal, not invented details.

Check the boxes below after the service is live and the smoke test passes.

- [ ] One Render web service serves the app and the API
- [ ] Production env: Supabase, OpenAI, `DATABASE_URL` (direct 5432), backend secrets
- [ ] Alembic migrations applied on the production database
- [ ] Health check and a smoke test: upload and chat in the browser on the Render URL

## Minimum viable product

The API can be called from a terminal before the screens exist. That does not count. He uploads and asks in the browser.

- [x] Upload one itinerary PDF in the app and see it become ready
- [x] Ask a question in the chat and get an answer that cites the page
- [x] Both of those happen in the browser, not by calling the API from a terminal
- [ ] Same upload and chat flow works on the deployed Render app (not localhost)
