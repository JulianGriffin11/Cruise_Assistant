# Cruise Assistant

Internal tool for a cruise operator. Upload a package itinerary PDF (about 20 pages, a few per year), then ask questions grounded in those docs. Answers cite the cruise and the page. The open chat thread stays in the browser and clears on refresh.

Check a box when that step is done.

## Phase 1 — Skeleton

- [ ] Python project with FastAPI, settings, and a SQLAlchemy session
- [ ] Alembic set up against the direct Supabase database URL (port 5432)
- [ ] Supabase Postgres with the `vector` extension
- [ ] Supabase Storage bucket `itineraries` for the original PDFs
- [ ] Health check that confirms the API can reach the database

## Phase 2 — Data model

- [ ] `cruises` table: name, year, optional start and end dates
- [ ] `documents` table: cruise, filename, storage path, page count, status, error message
- [ ] `chunks` table: document, cruise, page number, chunk index, text, embedding `vector(1536)`
- [ ] First migration creates the `vector` extension and these three tables
- [ ] No conversation or message tables in this version

## Phase 3 — Ingest

- [ ] `POST /documents` accepts a PDF, stores it, and returns while status is `processing`
- [ ] Background ingest extracts text per page with PyMuPDF
- [ ] Empty text marks the document `failed` (scanned PDFs are out of scope)
- [ ] Chunk by page, about 500–800 tokens, with overlap and the page number kept
- [ ] Embed chunks with `text-embedding-3-small` and insert them
- [ ] Status ends as `ready` or `failed`, with `GET /documents/{id}` for the UI to poll
- [ ] `POST /documents/{id}/retry` re-runs a failed ingest

## Phase 4 — Ask

- [ ] `POST /chat` accepts the question, an optional cruise, and the recent turns already on screen
- [ ] Embed the question and search the top 8 chunks by cosine distance
- [ ] Drop weak matches, and filter by cruise when one is selected
- [ ] Stream a grounded answer, then send citations (cruise name and page)
- [ ] Prompt quotes dates and prices only when the chunks contain them, and says when the docs do not
- [ ] A request to draft an email is the same chat call; page citations stay under the reply, not inside the letter
- [ ] Nothing about the thread is written to the database

## Phase 5 — Frontend

- [ ] Vite, React, TypeScript, and Tailwind
- [ ] shadcn/ui init, with button, input, textarea, card, select, badge, dialog, scroll-area, separator, alert, and skeleton
- [ ] Library page: cruise cards, dialog to create a cruise, PDF upload
- [ ] Library page: status badge and skeleton while a document is processing
- [ ] Chat page: cruise select (or search all), scroll area, textarea, and send button
- [ ] Chat page: stream the reply and show cruise name and page under each answer
- [ ] Thread lives in React state and clears on refresh

## Phase 6 — Check the path

- [ ] Upload one real itinerary and wait until it is `ready`
- [ ] Ask a question whose answer is on a known page and confirm that page is cited
- [ ] Ask a question the PDF does not answer and confirm it does not invent details

## Minimum viable product

The API can be called from a terminal before the screens exist. That does not count. He uploads and asks in the browser.

- [ ] Upload one itinerary PDF in the app and see it become ready
- [ ] Ask a question in the chat and get an answer that cites the page
- [ ] Both of those happen in the browser, not by calling the API from a terminal
