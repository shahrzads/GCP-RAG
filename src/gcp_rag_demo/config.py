"""Configuration loading for the GCP RAG demo."""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for unit tests
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()


@dataclass
class Settings:
    """Runtime settings loaded from environment variables."""

    project_id: str
    location: str
    bucket_name: Optional[str]
    embedding_model: str
    embedding_dimension: int
    generation_model: str
    generation_temperature: float
    generation_max_output_tokens: int
    vector_search_index_name: Optional[str]
    vector_search_index_display_name: str
    vector_search_index_endpoint_name: Optional[str]
    vector_search_index_endpoint_display_name: str
    vector_search_deployed_index_id: str
    vector_search_index_update_method: str
    vector_search_artifact_prefix: str
    vector_search_approximate_neighbors_count: int
    vector_search_leaf_node_embedding_count: int
    vector_search_leaf_nodes_to_search_percent: int
    vector_search_network: Optional[str]
    index_artifact_blob: str
    chunk_preview_blob: str
    source_artifact_prefix: str
    chunk_size: int
    chunk_overlap: int


def _require_env(name: str) -> str:
    """Return a required environment variable or raise a helpful error."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            "{name} is required. Copy .env.example to .env and set your Google Cloud project values.".format(
                name=name
            )
        )
    return value


def get_settings() -> Settings:
    """Build the application settings object from the current environment."""
    return Settings(
        project_id=_require_env("GCP_PROJECT_ID"),
        location=os.getenv("GCP_LOCATION", "us-central1").strip(),
        bucket_name=os.getenv("GCS_BUCKET_NAME", "").strip() or None,
        embedding_model=os.getenv("EMBEDDING_MODEL", "gemini-embedding-001").strip(),
        embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "768")),
        generation_model=os.getenv("GENERATION_MODEL", "gemini-2.5-flash").strip(),
        generation_temperature=float(os.getenv("GENERATION_TEMPERATURE", "0.2")),
        generation_max_output_tokens=int(os.getenv("GENERATION_MAX_OUTPUT_TOKENS", "512")),
        vector_search_index_name=os.getenv("VECTOR_SEARCH_INDEX_NAME", "").strip() or None,
        vector_search_index_display_name=os.getenv("VECTOR_SEARCH_INDEX_DISPLAY_NAME", "gcp-rag-demo-index").strip(),
        vector_search_index_endpoint_name=os.getenv("VECTOR_SEARCH_INDEX_ENDPOINT_NAME", "").strip() or None,
        vector_search_index_endpoint_display_name=os.getenv(
            "VECTOR_SEARCH_INDEX_ENDPOINT_DISPLAY_NAME", "gcp-rag-demo-endpoint"
        ).strip(),
        vector_search_deployed_index_id=os.getenv("VECTOR_SEARCH_DEPLOYED_INDEX_ID", "rag_demo_index").strip(),
        vector_search_index_update_method=os.getenv("VECTOR_SEARCH_INDEX_UPDATE_METHOD", "STREAM_UPDATE").strip(),
        vector_search_artifact_prefix=os.getenv(
            "VECTOR_SEARCH_ARTIFACT_PREFIX", "interview-rag-demo/vector-search"
        ).strip(),
        vector_search_approximate_neighbors_count=int(
            os.getenv("VECTOR_SEARCH_APPROXIMATE_NEIGHBORS_COUNT", "10")
        ),
        vector_search_leaf_node_embedding_count=int(
            os.getenv("VECTOR_SEARCH_LEAF_NODE_EMBEDDING_COUNT", "500")
        ),
        vector_search_leaf_nodes_to_search_percent=int(
            os.getenv("VECTOR_SEARCH_LEAF_NODES_TO_SEARCH_PERCENT", "10")
        ),
        vector_search_network=os.getenv("VECTOR_SEARCH_NETWORK", "").strip() or None,
        index_artifact_blob=os.getenv("INDEX_ARTIFACT_BLOB", "interview-rag-demo/artifacts/index.json").strip(),
        chunk_preview_blob=os.getenv("CHUNK_PREVIEW_BLOB", "interview-rag-demo/artifacts/chunks.jsonl").strip(),
        source_artifact_prefix=os.getenv("SOURCE_ARTIFACT_PREFIX", "interview-rag-demo/raw").strip(),
        chunk_size=int(os.getenv("CHUNK_SIZE", "550")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "120")),
    )
