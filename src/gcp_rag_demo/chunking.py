"""Helpers for splitting source documents into retrieval-friendly chunks."""

import re
from typing import Iterable
from typing import List

from gcp_rag_demo.models import DocumentChunk
from gcp_rag_demo.models import SourceDocument

WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Collapse repeated whitespace and trim surrounding space."""
    return WHITESPACE_PATTERN.sub(" ", text).strip()


def _split_text(text: str, max_chars: int, overlap_chars: int) -> List[str]:
    """Split text with LangChain's sentence-aware character splitter."""
    normalized = normalize_text(text)
    if not normalized:
        return []

    try:
        from langchain_text_splitters import CharacterTextSplitter
    except ImportError as exc:  # pragma: no cover - depends on external package
        raise RuntimeError(
            "langchain-text-splitters is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
        ) from exc

    splitter = CharacterTextSplitter(
        separator=r"(?<=[.!?])\s+",
        is_separator_regex=True,
        chunk_size=max_chars,
        chunk_overlap=overlap_chars,
    )
    return [chunk.strip() for chunk in splitter.split_text(normalized) if chunk.strip()]


def chunk_document(
    document: SourceDocument,
    max_chars: int = 550,
    overlap_chars: int = 120,
) -> List[DocumentChunk]:
    """Break one source document into overlapping character-bounded chunks."""
    chunk_texts = _split_text(document.text, max_chars=max_chars, overlap_chars=overlap_chars)
    chunks = []
    for chunk_text in chunk_texts:
        chunks.append(
            DocumentChunk(
                chunk_id="{0}-chunk-{1:02d}".format(document.doc_id, len(chunks)),
                doc_id=document.doc_id,
                title=document.title,
                category=document.category,
                text=chunk_text,
                source_uri=document.source_uri,
                chunk_index=len(chunks),
            )
        )

    return chunks


def chunk_documents(
    documents: Iterable[SourceDocument],
    max_chars: int = 550,
    overlap_chars: int = 120,
) -> List[DocumentChunk]:
    """Chunk each source document and return the combined chunk list."""
    chunks = []
    for document in documents:
        chunks.extend(chunk_document(document, max_chars=max_chars, overlap_chars=overlap_chars))
    return chunks
