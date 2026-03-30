"""Utilities for loading source data and saving retrieval artifacts."""

import hashlib
import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict
from typing import Iterable
from typing import List
from typing import Tuple

from gcp_rag_demo.models import DocumentChunk
from gcp_rag_demo.models import IndexEntry
from gcp_rag_demo.models import SourceDocument

SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def load_source_documents(path: str) -> List[SourceDocument]:
    """Load source documents from a JSONL file, PDF file, or directory of PDFs."""
    candidate = Path(path)
    if candidate.is_dir():
        pdf_paths = sorted(item for item in candidate.iterdir() if item.suffix.lower() == ".pdf")
        if not pdf_paths:
            raise RuntimeError("No PDF files were found in: {0}".format(path))
        documents = []
        for pdf_path in pdf_paths:
            documents.extend(load_pdf_documents(str(pdf_path)))
        return documents

    if candidate.suffix.lower() == ".pdf":
        return load_pdf_documents(path)
    if candidate.suffix.lower() != ".jsonl":
        raise RuntimeError("Unsupported source format: {0}".format(candidate.suffix or path))

    return load_jsonl_source_documents(path)


def load_jsonl_source_documents(path: str) -> List[SourceDocument]:
    """Load source documents from a JSONL dataset."""
    documents = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            documents.append(
                SourceDocument(
                    doc_id=payload["id"],
                    title=payload["title"],
                    category=payload.get("category", "general"),
                    text=payload["text"],
                    source_uri=payload.get("source_uri", "local://line-{0}".format(line_number)),
                )
            )
    return documents


def _slugify_filename(filename: str) -> str:
    """Build a stable ASCII slug from a filename."""
    stem = Path(filename).stem.lower()
    slug = SLUG_PATTERN.sub("-", stem).strip("-")
    return slug or "document"


def _build_pdf_document_id(filename: str, content: bytes) -> str:
    """Build a deterministic document ID for a PDF."""
    digest = hashlib.sha1(content).hexdigest()[:8]
    return "{0}-{1}".format(_slugify_filename(filename), digest)


def extract_pdf_text(content: bytes) -> str:
    """Extract text from a non-OCR PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - depends on external package
        raise RuntimeError(
            "pypdf is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
        ) from exc

    reader = PdfReader(BytesIO(content))
    page_texts = []
    for page in reader.pages:
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            text = page.extract_text() or ""
        if text.strip():
            page_texts.append(text)

    extracted_text = "\n\n".join(page_texts).strip()
    if not extracted_text:
        raise RuntimeError("No text could be extracted from the provided PDF.")
    return extracted_text


def source_document_from_pdf_bytes(
    filename: str,
    content: bytes,
    source_uri: str,
    category: str = "pdf",
) -> SourceDocument:
    """Convert one uploaded PDF into a source document."""
    return SourceDocument(
        doc_id=_build_pdf_document_id(filename, content),
        title=Path(filename).stem,
        category=category,
        text=extract_pdf_text(content),
        source_uri=source_uri,
    )


def load_pdf_documents(path: str) -> List[SourceDocument]:
    """Load one PDF file into a source document."""
    pdf_path = Path(path)
    return [
        source_document_from_pdf_bytes(
            filename=pdf_path.name,
            content=pdf_path.read_bytes(),
            source_uri=pdf_path.resolve().as_uri(),
        )
    ]


def serialize_chunk_preview(chunks: Iterable[DocumentChunk]) -> str:
    """Serialize chunk data as JSONL preview content."""
    return "".join(json.dumps(chunk.to_dict(), ensure_ascii=True) + "\n" for chunk in chunks)


def _build_index_payload(
    entries: Iterable[IndexEntry],
    metadata: Dict[str, object],
) -> Dict[str, object]:
    """Build the JSON-serializable index payload."""
    return {
        "metadata": {
            "created_at": datetime.utcnow().isoformat() + "Z",
            **metadata,
        },
        "entries": [entry.to_dict() for entry in entries],
    }


def serialize_index(
    entries: Iterable[IndexEntry],
    metadata: Dict[str, object],
) -> str:
    """Serialize the retrieval index and metadata as JSON."""
    return json.dumps(_build_index_payload(entries, metadata), indent=2, ensure_ascii=True)


def serialize_vector_search_input(entries: Iterable[IndexEntry]) -> str:
    """Serialize embeddings as newline-delimited JSON records for Vector Search."""
    return "".join(
        json.dumps(
            {
                "id": entry.chunk.chunk_id,
                "embedding": entry.embedding,
            },
            ensure_ascii=True,
        )
        + "\n"
        for entry in entries
    )


def extract_index_metadata(serialized_index: str) -> Dict[str, object]:
    """Return only the metadata section from a serialized index payload."""
    payload = json.loads(serialized_index)
    return dict(payload.get("metadata", {}))


def deserialize_index(serialized_index: str) -> Tuple[Dict[str, object], List[IndexEntry]]:
    """Load a serialized index payload into metadata and index entries."""
    payload = json.loads(serialized_index)

    entries = []
    for raw_entry in payload["entries"]:
        chunk_payload = raw_entry["chunk"]
        chunk = DocumentChunk(
            chunk_id=chunk_payload["chunk_id"],
            doc_id=chunk_payload["doc_id"],
            title=chunk_payload["title"],
            category=chunk_payload["category"],
            text=chunk_payload["text"],
            source_uri=chunk_payload["source_uri"],
            chunk_index=chunk_payload["chunk_index"],
        )
        entries.append(IndexEntry(chunk=chunk, embedding=raw_entry["embedding"]))

    return payload["metadata"], entries
