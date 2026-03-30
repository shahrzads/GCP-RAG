"""Command-line entry points for ingesting data and querying the demo index."""

import argparse

from gcp_rag_demo.config import get_settings
from gcp_rag_demo.data_io import load_source_documents
from gcp_rag_demo.pipeline import ingest_documents
from gcp_rag_demo.pipeline import query_documents
from gcp_rag_demo.storage import GCSArtifactStore


def _print_answer(question, answer) -> None:
    """Render the grounded answer to standard output."""
    print("Question: {0}".format(question))
    print("")
    print("Answer:")
    print(answer)
    print("")


def _print_results(results) -> None:
    """Render ranked retrieval results to standard output."""
    print("Retrieved chunks:")
    print("")
    for index, result in enumerate(results, start=1):
        print("{0}. score={1:.4f} | {2}".format(index, result.score, result.title))
        print("   chunk_id: {0}".format(result.chunk_id))
        print("   source:   {0}".format(result.source_uri))
        print("   text:     {0}".format(result.text))
        print("")


def _upload_source_artifact(settings, source, prefix) -> None:
    """Upload the source dataset to Cloud Storage."""
    if not settings.bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME must be set before using --upload-artifacts.")

    store = GCSArtifactStore(project_id=settings.project_id, bucket_name=settings.bucket_name)
    prefix = prefix.strip("/ ")
    blob_name = "{0}/{1}".format(prefix, source.split("/")[-1])
    uri = store.upload_file(source, blob_name)
    print("Uploaded source:")
    print("- {0} -> {1}".format(source, uri))


def handle_ingest(args) -> None:
    """Run the ingest workflow and persist retrieval artifacts in GCP."""
    settings = get_settings()
    documents = load_source_documents(args.source)
    result = ingest_documents(
        documents,
        settings,
        output_blob=args.output,
        preview_blob=args.preview,
        embedding_model=args.embedding_model,
        embedding_dimension=args.embedding_dimension,
        max_chars=args.chunk_size,
        overlap_chars=args.chunk_overlap,
    )

    print("Ingestion finished.")
    print("- documents: {0}".format(result.document_count))
    print("- chunks:    {0}".format(result.chunk_count))
    print("- preview:   {0}".format(result.preview_uri))
    print("- index:     {0}".format(result.index_uri))
    print("- vector input: {0}".format(result.vector_input_uri))
    print("- vector index: {0}".format(result.vector_index_name))
    print("- vector endpoint: {0}".format(result.vector_endpoint_name))

    if args.upload_artifacts:
        print("")
        _upload_source_artifact(settings, args.source, args.upload_prefix or settings.source_artifact_prefix)


def handle_query(args) -> None:
    """Embed a question, retrieve relevant chunks, and optionally generate an answer."""
    settings = get_settings()
    result = query_documents(
        args.question,
        settings,
        index_blob=args.index,
        top_k=args.top_k,
        generation_model=args.generation_model,
        retrieval_only=args.retrieval_only,
    )

    if result.answer is not None:
        _print_answer(args.question, result.answer)
    _print_results(result.results)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(description="Simple GCP RAG demo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Chunk documents, upload artifacts to GCS, and sync Vector Search")
    ingest.add_argument("--source", required=True, help="Path to a JSONL file, PDF file, or directory of PDFs")
    ingest.add_argument("--output", default=None, help="GCS blob name for the JSON index artifact")
    ingest.add_argument(
        "--preview",
        default=None,
        help="GCS blob name for the human-readable chunk preview",
    )
    ingest.add_argument("--chunk-size", type=int, default=None, help="Maximum characters per chunk")
    ingest.add_argument("--chunk-overlap", type=int, default=None, help="Overlap between chunk windows")
    ingest.add_argument("--embedding-model", default=None, help="Vertex AI embedding model")
    ingest.add_argument("--embedding-dimension", type=int, default=None, help="Embedding vector size")
    ingest.add_argument("--upload-artifacts", action="store_true", help="Upload the source dataset to GCS")
    ingest.add_argument(
        "--upload-prefix",
        default=None,
        help="Cloud Storage prefix used when uploading the source dataset",
    )
    ingest.set_defaults(handler=handle_ingest)

    query = subparsers.add_parser("query", help="Run a grounded RAG query against the GCS-hosted index artifact")
    query.add_argument("--index", default=None, help="GCS blob name for the stored JSON index artifact")
    query.add_argument("--question", required=True, help="User question")
    query.add_argument("--top-k", type=int, default=3, help="Number of chunks to return")
    query.add_argument("--generation-model", default=None, help="Vertex AI generative model")
    query.add_argument("--retrieval-only", action="store_true", help="Skip answer generation and print chunks only")
    query.set_defaults(handler=handle_query)

    return parser


def main() -> None:
    """Parse CLI arguments and dispatch to the selected command handler."""
    parser = build_parser()
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
