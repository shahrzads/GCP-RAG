import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcp_rag_demo.chunking import chunk_document
from gcp_rag_demo.models import SourceDocument


class ChunkingTests(unittest.TestCase):
    def test_chunk_document_preserves_overlap_and_metadata(self):
        document = SourceDocument(
            doc_id="doc-123",
            title="Chunking Test",
            category="tests",
            source_uri="kb://tests/chunking",
            text=(
                "Sentence one explains the setup. "
                "Sentence two is intentionally a little longer to create pressure on the chunk size. "
                "Sentence three continues the example with more detail. "
                "Sentence four should land in a later chunk."
            ),
        )

        chunks = chunk_document(document, max_chars=110, overlap_chars=45)

        self.assertGreaterEqual(len(chunks), 4)
        self.assertEqual(chunks[0].doc_id, "doc-123")
        self.assertEqual(chunks[0].title, "Chunking Test")
        self.assertIn("Sentence one", chunks[0].text)
        self.assertIn("Sentence one", chunks[1].text)
        self.assertIn("Sentence two", chunks[1].text)
        self.assertIn("Sentence two", chunks[2].text)


if __name__ == "__main__":
    unittest.main()
