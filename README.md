# Cruise Assistant

This is a question tool built for a cruise business. The owner uploads a package PDF, asks a question, and gets an answer that cites the cruise and the page.

## Why I Built This 💡

The business owner needed a faster way to read a package itinerary. Instead of hunting through about twenty pages for a date, a price, or a port, they needed the answer pulled from the document, with the page it came from.

## How It Works

```text
       Upload Itinerary
              ↓
         Extract Text
              ↓
        Chunk and Embed
              ↓
         SQL Postgres
              ↓
         Hybrid Search
              ↓
        Grounded Answer
```

Upload a PDF. Python extracts the text with PyMuPDF, splits it by page, and stores embeddings in Postgres. A question searches those chunks with full-text and vector search, then the model writes from the passages that matched. One Render deployment serves the React UI and the API together.

## Tech Stack 🛠️


| Technology        | Purpose                                    |
| ----------------- | ------------------------------------------ |
| React / Vite      | Library page and chat UI                   |
| Python            | PDF extract, chunking, search, and answers |
| Supabase Postgres | Cruises, documents, chunks, and vectors    |
| Supabase Storage  | Original itinerary PDFs                    |
| OpenAI API        | Embeddings and grounded answers            |
| Render            | One web service for the UI and the API     |


## AI Pipeline 🤖

Python and SQL handle extraction, chunking, embeddings, and ranking. The model is used only to write from the passages that search already returned.

1. Extract the itinerary and chunk it by page
2. Embed each chunk and store the vector
3. Search with Postgres full-text and cosine distance, then merge the hits
4. Stream an answer, then send the cruise name and page

Dates and prices are quoted only when they appear in those passages. If the documents do not say, the answer says so. A request to draft an email uses the same call. Page citations stay under the reply, not inside the letter.

## Database 🗄️

Supabase Postgres stores the cruise, the uploaded document, and the chunks. Each chunk keeps its page number and a `vector(1536)` embedding. The original PDF goes in the `itineraries` storage bucket. The open chat thread stays in the browser and clears on refresh. Nothing about the thread is written to the database.

## What I Learned 📚

Building this was less about the model call and more about the pipeline around it. The owner needed every answer to name the page, and the model will invent a date when the prompt lets it.

Predictable work belongs in Python. Extraction, chunking, search, and citations stay deterministic. The model is reserved for the written answer.

## Future Improvements 🚀

- Expand to different file types (images and spreadsheets)
- Confirm upload and chat on the live Render URL

## Project Status ✅

The path is built: upload a PDF, wait until it is ready, ask in the browser, and get an answer that cites the page. A question the document does not answer is refused. It is set up to deploy as one Render web service.