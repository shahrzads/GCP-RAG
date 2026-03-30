import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcp_rag_demo.data_io import deserialize_index
from gcp_rag_demo.data_io import extract_index_metadata
from gcp_rag_demo.data_io import serialize_chunk_preview
from gcp_rag_demo.data_io import serialize_index
from gcp_rag_demo.data_io import serialize_vector_search_input
from gcp_rag_demo.models import DocumentChunk
from gcp_rag_demo.models import IndexEntry


class DataIOTests(unittest.TestCase):
    def test_serialize_and_deserialize_index_round_trip(self):
        entries = [
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-a",
                    doc_id="doc-a",
                    title="Cloud Storage",
                    category="storage",
                    text="Cloud Storage holds chunk metadata in GCS.",
                    source_uri="kb://storage",
                    chunk_index=0,
                ),
                embedding=[0.1, 0.2, 0.3],
            )
        ]

        serialized = serialize_index(entries, metadata={"vector_search_index_name": "indexes/123"})
        metadata, restored_entries = deserialize_index(serialized)

        self.assertEqual(metadata["vector_search_index_name"], "indexes/123")
        self.assertEqual(restored_entries[0].chunk.chunk_id, "chunk-a")
        self.assertEqual(restored_entries[0].embedding, [0.1, 0.2, 0.3])

    def test_extract_index_metadata_reads_metadata_without_entry_access(self):
        serialized = serialize_index([], metadata={"chunk_count": 0, "vector_search_index_name": "indexes/456"})

        metadata = extract_index_metadata(serialized)

        self.assertEqual(metadata["chunk_count"], 0)
        self.assertEqual(metadata["vector_search_index_name"], "indexes/456")

    def test_serialize_chunk_preview_returns_jsonl(self):
        chunks = [
            DocumentChunk(
                chunk_id="chunk-a",
                doc_id="doc-a",
                title="Cloud Storage",
                category="storage",
                text="Chunk preview text.",
                source_uri="kb://storage",
                chunk_index=0,
            )
        ]

        serialized = serialize_chunk_preview(chunks)

        self.assertIn('"chunk_id": "chunk-a"', serialized)
        self.assertTrue(serialized.endswith("\n"))

    def test_serialize_vector_search_input_returns_newline_delimited_json_records(self):
        entries = [
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-a",
                    doc_id="doc-a",
                    title="Cloud Storage",
                    category="storage",
                    text="Chunk preview text.",
                    source_uri="kb://storage",
                    chunk_index=0,
                ),
                embedding=[0.1, 0.2, 0.3],
            )
        ]

        serialized = serialize_vector_search_input(entries)

        self.assertIn('"id": "chunk-a"', serialized)
        self.assertIn('"embedding": [0.1, 0.2, 0.3]', serialized)
        self.assertTrue(serialized.endswith("\n"))


if __name__ == "__main__":
    unittest.main()
