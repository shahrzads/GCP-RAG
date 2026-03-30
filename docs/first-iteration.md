# First Iteration Plan

This is the easiest version of the project that still looks credible in an interview.

## Objective

Build a simple semantic retrieval system with:

- a small JSONL dataset,
- Vertex AI embeddings,
- a local searchable index,
- optional Cloud Storage artifact uploads,
- a query CLI that returns top chunks with citations.

## Suggested Development Order

### 1. Create The Dataset

Start with `5` to `10` short documents in `JSONL` format.

Each record should have:

- `id`
- `title`
- `category`
- `source_uri`
- `text`

Keep the dataset small enough to inspect manually.

### 2. Implement Chunking

Split documents into retrieval-sized chunks.

Goals:

- keep chunks readable,
- preserve source ids,
- include chunk ids,
- use a small overlap between adjacent chunks.

### 3. Add Vertex AI Embeddings

Embed:

- chunks with `RETRIEVAL_DOCUMENT`
- user questions with `RETRIEVAL_QUERY`

Store only what you need in the saved index:

- chunk metadata
- chunk text
- embedding vector

### 4. Save Local Artifacts

Create two generated files:

- `chunks.jsonl` for human inspection
- `index.json` for retrieval

This keeps debugging easy.

### 5. Add Retrieval

For the first iteration:

- load the saved index,
- embed the question,
- compute cosine similarity,
- return the top `k` chunks with scores.

Do not add answer generation yet unless time allows.

### 6. Add Cloud Storage Uploads

This step is optional for local development, but useful for the interview:

- upload the original dataset,
- upload the chunk preview,
- upload the built index.

That lets you say the project already has a durable artifact store on GCP.

### 7. Add Evaluation

Once retrieval works, add a short list of expected results:

- question
- relevant chunk ids
- top-k threshold

You can then compute simple recall metrics later.

## What To Demo

Show three things:

1. the source data file,
2. the ingestion command,
3. the query output with source references.

That is enough to demonstrate the "R" part of RAG clearly.

## What To Say If Asked About Scale

Use this framing:

"For the first iteration, I optimized for correctness, readability, and a fast demo. I used Vertex AI for embeddings and Cloud Storage for artifacts, then kept the search index local because the dataset is intentionally small. The next step is moving the same vectors into Vertex AI Vector Search and wrapping the flow with Cloud Run."

