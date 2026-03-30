# Architecture

## First Iteration

```text
JSONL documents
      |
      v
Chunking module
      |
      v
Vertex AI embeddings
      |
      v
Local JSON index + chunk preview
      |
      +--> optional upload to Cloud Storage
      |
      v
Query embedding + cosine similarity
      |
      v
Top-k retrieved chunks with source metadata
```

## Why This Design Works Well For An Interview

- It proves the retrieval pipeline end to end.
- It uses real Google Cloud services where they matter most for the topic.
- It avoids a heavy deployment path for a tiny dataset.
- It leaves a very clear migration path to managed vector search.

## GCP Resource Plan

Use these resources for the first milestone:

- `Vertex AI API`
- `Cloud Storage bucket`
- `ADC` for local development authentication

Recommended defaults:

- Region: `us-central1`
- Embedding model: `gemini-embedding-001`
- Output dimension: `768`

## Upgrade Path

After the first iteration is stable:

1. Keep the same source dataset and chunking logic.
2. Keep the same Vertex AI embedding flow.
3. Replace the local JSON index with Vertex AI Vector Search.
4. Add a Cloud Run API for online queries.
5. Add Gemini answer generation on top of retrieved chunks.
6. Add evaluation and monitoring.

## Tradeoff Summary

Choose local retrieval first when:

- the dataset is small,
- you want a fast demo,
- cost matters,
- readability matters more than scale.

Choose Vector Search next when:

- the dataset grows beyond a toy scale,
- retrieval latency matters,
- approximate nearest neighbor search becomes useful,
- you want a more production-shaped architecture.

