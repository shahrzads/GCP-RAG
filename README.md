# GCP RAG Demo

An interview-friendly first iteration of a simple Retrieval Augmented Generation (RAG) system on Google Cloud.

This repo keeps the scope intentionally small:

- `pypdf` extracts text from non-OCR PDF uploads.
- `Vertex AI` creates document and query embeddings.
- `Vertex AI Vector Search` manages vector indexing and nearest-neighbor retrieval.
- `Gemini on Vertex AI` generates grounded answers from retrieved chunks.
- `Cloud Storage` is the home for raw documents and generated artifacts.

The result is a repo you can walk through in 5 to 10 minutes during an interview without hand-waving the hard parts.

## Why This Version

For a small interview dataset, the hardest part is usually not "semantic search at scale". It is proving that you can:

1. structure documents,
2. generate embeddings correctly,
3. build a retrievable index,
4. return the most relevant chunks with citations, and
5. explain how the design grows on GCP.

## Repo Layout

```text
.
├── .env.example
├── .github
│   └── workflows
│       ├── ci.yml
│       ├── deploy.yml
│       └── terraform.yml
├── .gitignore
├── .streamlit
│   └── config.toml
├── Dockerfile
├── data
│   ├── processed
│   │   └── .gitkeep
│   └── source_documents.jsonl
├── docs
│   ├── architecture.md
│   ├── deployment.md
│   └── first-iteration.md
├── infra
│   └── terraform
│       ├── main.tf
│       ├── outputs.tf
│       ├── terraform.tfvars.example
│       ├── variables.tf
│       └── versions.tf
├── pyproject.toml
├── src
│   └── gcp_rag_demo
│       ├── __init__.py
│       ├── chunking.py
│       ├── cli.py
│       ├── config.py
│       ├── data_io.py
│       ├── embeddings.py
│       ├── models.py
│       ├── retrieval.py
│       └── storage.py
└── tests
    ├── test_chunking.py
    └── test_retrieval.py
```

## GCP Services Used

- `Vertex AI` for `gemini-embedding-001`
- `Vertex AI Vector Search` for managed vector indexing and retrieval
- `Gemini on Vertex AI` for grounded answer generation
- `Cloud Storage` for source docs and generated artifacts
- `Application Default Credentials (ADC)` for local authentication

## Prerequisites

- Python `3.11+`
- `gcloud` CLI
- `docker`
- `terraform`
- A Google Cloud project with billing enabled
- Vertex AI API enabled
- Cloud Storage API enabled

## Local Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
cp .env.example .env
```

Update `.env` with your project details:

```bash
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GCS_BUCKET_NAME=your-rag-demo-bucket
VECTOR_SEARCH_ARTIFACT_PREFIX=interview-rag-demo/vector-search
```

Authenticate locally:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project "$GCP_PROJECT_ID"
```

Create a bucket for cloud artifacts and Vector Search input files:

```bash
gcloud storage buckets create "gs://$GCS_BUCKET_NAME" --location=US-CENTRAL1
```

## Run The Demo

Build the chunk index, upload artifacts to GCS, and sync Vertex AI Vector Search:

```bash
gcp-rag ingest \
  --source data/source_documents.jsonl \
  --output interview-rag-demo/artifacts/index.json \
  --preview interview-rag-demo/artifacts/chunks.jsonl
```

You can also ingest a single PDF or a directory of PDFs:

```bash
gcp-rag ingest --source ./docs/manual.pdf
gcp-rag ingest --source ./pdfs
```

Optionally upload the source file to Cloud Storage as well:

```bash
gcp-rag ingest \
  --source data/source_documents.jsonl \
  --output interview-rag-demo/artifacts/index.json \
  --preview interview-rag-demo/artifacts/chunks.jsonl \
  --upload-artifacts \
  --upload-prefix interview-rag-demo/raw
```

Run a RAG query:

```bash
gcp-rag query \
  --index interview-rag-demo/artifacts/index.json \
  --question "Why does this demo use Vertex AI Vector Search?" \
  --top-k 3
```

If you want to inspect retrieval without answer generation:

```bash
gcp-rag query \
  --index interview-rag-demo/artifacts/index.json \
  --question "Why does this demo use Vertex AI Vector Search?" \
  --top-k 3 \
  --retrieval-only
```

## UI

Run the simple upload-and-query UI with:

```bash
streamlit run src/gcp_rag_demo/ui.py
```

You can also run the same UI in a local container:

```bash
docker build -t gcp-rag-demo:local .
docker run --rm -p 8080:8080 --env-file .env gcp-rag-demo:local
```

The UI currently:

- accepts PDF uploads
- stores the uploaded PDFs in GCS
- extracts text with `pypdf`
- builds a session-scoped index in GCS and Vertex AI Vector Search
- lets the user ask questions against those uploaded PDFs

Example questions:

- `Why does iteration one avoid Vector Search?`
- `Which Google Cloud service stores source documents?`
- `How are query and document embeddings generated?`
- `What should iteration two change?`

## What Success Looks Like In The Interview

You should be able to explain this flow clearly:

1. documents start in JSONL,
2. the chunker creates retrieval-sized passages,
3. Vertex AI embeds each chunk with the `RETRIEVAL_DOCUMENT` task type,
4. the query is embedded with `RETRIEVAL_QUERY`,
5. Vertex AI Vector Search returns the top chunk IDs,
6. the GCS-hosted index artifact maps those IDs back to chunk text,
7. Gemini generates a grounded answer using those chunks, and
8. the output still includes source metadata for inspection.

## Iteration Roadmap

- `Iteration 1`: Vertex AI embeddings + Vector Search + Gemini answer generation + Cloud Storage artifacts
- `Iteration 2`: replace the GCS-hosted index artifact with a managed metadata store
- `Iteration 3`: wrap retrieval in a Cloud Run API
- `Iteration 4`: add evaluation, prompt templates, and monitoring

## CI/CD And Terraform

This branch now includes:

- `GitHub Actions` CI for Python test runs
- `GitHub Actions` CD for Docker build, Artifact Registry push, and Cloud Run deploy
- `Terraform` for the bucket, Artifact Registry repository, Cloud Run service, service accounts, and GitHub OIDC federation

The exact bring-up steps live in [docs/deployment.md](docs/deployment.md). The short version is:

1. Run local tests with `python -m pytest`.
2. Build the Docker image locally with `docker build -t gcp-rag-demo:local .`.
3. Apply `infra/terraform` after filling in `terraform.tfvars`.
4. Copy the Terraform outputs into the GitHub Actions repository variables and secrets.
5. Push directly to a branch or open a PR to `dev` to run CI, then merge the PR to `dev` to trigger deployment.

## Current Notes

- The included unit tests cover chunking, serialization, Vector Search result mapping, and prompt-building logic only. They do not call Google Cloud services.
- PDF support currently assumes text-based PDFs and does not perform OCR.

## Notes On Vertex AI SDKs

- Embeddings in this repo still use `google-cloud-aiplatform`.
- Answer generation uses `google-genai`, which Google currently recommends for Gemini API usage on Vertex AI.
