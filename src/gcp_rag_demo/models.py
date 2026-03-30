"""Data models used across ingestion, indexing, and retrieval."""

from dataclasses import asdict
from dataclasses import dataclass
from typing import Dict
from typing import List


@dataclass
class SourceDocument:
    """A raw source document before chunking."""

    doc_id: str
    title: str
    category: str
    text: str
    source_uri: str

    def to_dict(self) -> Dict[str, str]:
        """Return a serialized form using the external ``id`` field name."""
        payload = asdict(self)
        payload["id"] = payload.pop("doc_id")
        return payload


@dataclass
class DocumentChunk:
    """A chunked segment of a source document."""

    chunk_id: str
    doc_id: str
    title: str
    category: str
    text: str
    source_uri: str
    chunk_index: int

    def to_dict(self) -> Dict[str, str]:
        """Return the chunk as a plain dictionary."""
        return asdict(self)


@dataclass
class IndexEntry:
    """A searchable index record combining a chunk and its embedding."""

    chunk: DocumentChunk
    embedding: List[float]

    def to_dict(self) -> Dict[str, object]:
        """Return a JSON-serializable representation of the index entry."""
        return {
            "chunk": self.chunk.to_dict(),
            "embedding": self.embedding,
        }


@dataclass
class RetrievalResult:
    """A ranked retrieval hit returned to the user."""

    chunk_id: str
    doc_id: str
    title: str
    source_uri: str
    score: float
    text: str
