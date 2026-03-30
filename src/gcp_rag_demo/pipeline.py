"""Shared ingestion and query workflows for the CLI and UI."""

from dataclasses import dataclass
from typing import List
from typing import Optional
from typing import Sequence

from gcp_rag_demo.chunking import chunk_documents
from gcp_rag_demo.data_io import deserialize_index
from gcp_rag_demo.data_io import extract_index_metadata
from gcp_rag_demo.data_io import serialize_chunk_preview
from gcp_rag_demo.data_io import serialize_index
from gcp_rag_demo.data_io import serialize_vector_search_input
from gcp_rag_demo.embeddings import VertexAIEmbeddingClient
from gcp_rag_demo.generation import VertexAIAnswerGenerator
from gcp_rag_demo.models import IndexEntry
from gcp_rag_demo.models import RetrievalResult
from gcp_rag_demo.models import SourceDocument
from gcp_rag_demo.retrieval import VertexAIVectorSearchRetriever
from gcp_rag_demo.retrieval import build_chunk_store
from gcp_rag_demo.storage import GCSArtifactStore


@dataclass
class IngestResult:
    """Summary of an ingestion run and its cloud artifacts."""

    document_count: int
    chunk_count: int
    preview_uri: str
    index_uri: str
    vector_input_uri: str
    vector_index_name: str
    vector_endpoint_name: str


@dataclass
class QueryResult:
    """Answer-generation result and retrieved chunks for a user question."""

    answer: Optional[str]
    results: List[RetrievalResult]


def _build_index_entries(chunks, embeddings) -> List[IndexEntry]:
    """Pair chunks with their embedding vectors for index serialization."""
    return [IndexEntry(chunk=chunk, embedding=embedding) for chunk, embedding in zip(chunks, embeddings)]


def _vector_search_blob_name(prefix: str) -> str:
    """Build the bucket-relative blob path for Vector Search input."""
    cleaned = prefix.strip("/ ")
    return "{0}/index-input.json".format(cleaned)


def _legacy_vector_search_blob_name(prefix: str) -> str:
    """Build the legacy Vector Search blob path used by earlier app versions."""
    cleaned = prefix.strip("/ ")
    return "{0}/index-input.jsonl".format(cleaned)


def _load_existing_metadata(store: GCSArtifactStore, blob_name: str):
    """Load metadata from a previously written cloud index artifact when present."""
    try:
        serialized_index = store.download_text(blob_name)
    except FileNotFoundError:
        return {}
    return extract_index_metadata(serialized_index)


def _load_existing_index(store: GCSArtifactStore, blob_name: str):
    """Load the previous cloud index artifact when present."""
    try:
        serialized_index = store.download_text(blob_name)
    except FileNotFoundError:
        return {}, []
    return deserialize_index(serialized_index)


def _sync_vector_search(
    settings,
    store,
    entries,
    dimensions,
    existing_metadata,
    existing_entries,
    vector_search_prefix=None,
):
    """Upload Vector Search input and ensure the managed index is ready."""
    prefix = vector_search_prefix or settings.vector_search_artifact_prefix
    blob_name = _vector_search_blob_name(prefix)
    store.delete_blob(_legacy_vector_search_blob_name(prefix))
    vector_input_uri = store.upload_text(
        blob_name,
        serialize_vector_search_input(entries),
        content_type="application/json",
    )
    contents_delta_uri = "gs://{0}/{1}".format(settings.bucket_name, prefix.strip("/ "))

    retriever = VertexAIVectorSearchRetriever(project_id=settings.project_id, location=settings.location)
    deployed_index_id = (
        existing_metadata.get("vector_search_deployed_index_id") or settings.vector_search_deployed_index_id
    )
    index_name, index_endpoint_name = retriever.ensure_index_ready(
        contents_delta_uri=contents_delta_uri,
        dimensions=dimensions,
        index_name=settings.vector_search_index_name or existing_metadata.get("vector_search_index_name"),
        index_display_name=settings.vector_search_index_display_name,
        index_endpoint_name=(
            settings.vector_search_index_endpoint_name or existing_metadata.get("vector_search_index_endpoint_name")
        ),
        index_endpoint_display_name=settings.vector_search_index_endpoint_display_name,
        deployed_index_id=str(deployed_index_id),
        index_update_method=settings.vector_search_index_update_method,
        entries=entries,
        previous_chunk_ids=[entry.chunk.chunk_id for entry in existing_entries],
        approximate_neighbors_count=settings.vector_search_approximate_neighbors_count,
        leaf_node_embedding_count=settings.vector_search_leaf_node_embedding_count,
        leaf_nodes_to_search_percent=settings.vector_search_leaf_nodes_to_search_percent,
        network=settings.vector_search_network,
    )
    return index_name, index_endpoint_name, vector_input_uri


def ingest_documents(
    documents: Sequence[SourceDocument],
    settings,
    output_blob: Optional[str] = None,
    preview_blob: Optional[str] = None,
    embedding_model: Optional[str] = None,
    embedding_dimension: Optional[int] = None,
    max_chars: Optional[int] = None,
    overlap_chars: Optional[int] = None,
    vector_search_prefix: Optional[str] = None,
    deployed_index_id: Optional[str] = None,
) -> IngestResult:
    """Chunk documents, persist artifacts to GCS, and sync Vector Search."""
    if not settings.bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME must be set to persist retrieval artifacts in GCP.")

    resolved_output_blob = output_blob or settings.index_artifact_blob
    resolved_preview_blob = preview_blob or settings.chunk_preview_blob
    resolved_embedding_model = embedding_model or settings.embedding_model
    resolved_embedding_dimension = embedding_dimension or settings.embedding_dimension
    resolved_max_chars = max_chars or settings.chunk_size
    resolved_overlap_chars = overlap_chars or settings.chunk_overlap

    store = GCSArtifactStore(project_id=settings.project_id, bucket_name=settings.bucket_name)
    existing_metadata, existing_entries = _load_existing_index(store, resolved_output_blob)
    if deployed_index_id:
        existing_metadata["vector_search_deployed_index_id"] = deployed_index_id

    chunks = chunk_documents(
        documents,
        max_chars=resolved_max_chars,
        overlap_chars=resolved_overlap_chars,
    )
    embedding_client = VertexAIEmbeddingClient(
        project_id=settings.project_id,
        location=settings.location,
        model_name=resolved_embedding_model,
        output_dimensionality=resolved_embedding_dimension,
    )
    embeddings = embedding_client.embed_documents(chunks)
    entries = _build_index_entries(chunks, embeddings)
    index_name, index_endpoint_name, vector_input_uri = _sync_vector_search(
        settings,
        store,
        entries,
        dimensions=resolved_embedding_dimension,
        existing_metadata=existing_metadata,
        existing_entries=existing_entries,
        vector_search_prefix=vector_search_prefix,
    )
    preview_uri = store.upload_text(
        resolved_preview_blob,
        serialize_chunk_preview(chunks),
        content_type="application/x-ndjson",
    )
    index_uri = store.upload_text(
        resolved_output_blob,
        serialize_index(
            entries,
            metadata={
                "project_id": settings.project_id,
                "location": settings.location,
                "embedding_model": resolved_embedding_model,
                "embedding_dimension": resolved_embedding_dimension,
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "vector_search_index_name": index_name,
                "vector_search_index_endpoint_name": index_endpoint_name,
                "vector_search_deployed_index_id": (
                    deployed_index_id
                    or existing_metadata.get("vector_search_deployed_index_id")
                    or settings.vector_search_deployed_index_id
                ),
                "vector_search_index_update_method": settings.vector_search_index_update_method,
            },
        ),
        content_type="application/json",
    )

    return IngestResult(
        document_count=len(documents),
        chunk_count=len(chunks),
        preview_uri=preview_uri,
        index_uri=index_uri,
        vector_input_uri=vector_input_uri,
        vector_index_name=index_name,
        vector_endpoint_name=index_endpoint_name,
    )


def query_documents(
    question: str,
    settings,
    index_blob: Optional[str] = None,
    top_k: int = 3,
    generation_model: Optional[str] = None,
    retrieval_only: bool = False,
) -> QueryResult:
    """Retrieve relevant chunks and optionally generate a grounded answer."""
    if not settings.bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME must be set to load retrieval artifacts from GCP.")

    resolved_index_blob = index_blob or settings.index_artifact_blob
    store = GCSArtifactStore(project_id=settings.project_id, bucket_name=settings.bucket_name)
    metadata, entries = deserialize_index(store.download_text(resolved_index_blob))
    chunk_store = build_chunk_store(entries)

    index_endpoint_name = str(
        metadata.get("vector_search_index_endpoint_name") or settings.vector_search_index_endpoint_name or ""
    ).strip()
    deployed_index_id = str(
        metadata.get("vector_search_deployed_index_id") or settings.vector_search_deployed_index_id
    ).strip()
    if not index_endpoint_name:
        raise RuntimeError(
            "Vector Search endpoint is not configured. Run ingest first or set VECTOR_SEARCH_INDEX_ENDPOINT_NAME."
        )

    embedding_client = VertexAIEmbeddingClient(
        project_id=settings.project_id,
        location=settings.location,
        model_name=str(metadata.get("embedding_model", settings.embedding_model)),
        output_dimensionality=int(metadata.get("embedding_dimension", settings.embedding_dimension)),
    )
    question_embedding = embedding_client.embed_query(question)
    retriever = VertexAIVectorSearchRetriever(
        project_id=settings.project_id,
        location=settings.location,
        index_endpoint_name=index_endpoint_name,
    )
    results = retriever.retrieve(
        question_embedding,
        chunk_store=chunk_store,
        deployed_index_id=deployed_index_id,
        top_k=top_k,
    )

    if retrieval_only:
        return QueryResult(answer=None, results=results)

    answer_generator = VertexAIAnswerGenerator(
        project_id=settings.project_id,
        location=settings.location,
        model_name=generation_model or settings.generation_model,
        temperature=settings.generation_temperature,
        max_output_tokens=settings.generation_max_output_tokens,
    )
    try:
        answer = answer_generator.generate_answer(question, results)
    finally:
        answer_generator.close()

    return QueryResult(answer=answer, results=results)
