import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcp_rag_demo.chunking import chunk_document
from gcp_rag_demo.models import SourceDocument


class ChunkingTests(unittest.TestCase):
    def test_chunk_document_uses_sentence_oriented_langchain_strategy(self):
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

        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0].doc_id, "doc-123")
        self.assertEqual(chunks[0].title, "Chunking Test")
        self.assertEqual(chunks[0].chunk_id, "doc-123-chunk-00")
        self.assertEqual(chunks[1].chunk_id, "doc-123-chunk-01")
        self.assertTrue(all(len(chunk.text) <= 110 for chunk in chunks))
        self.assertEqual(chunks[0].text, "Sentence one explains the setup")
        self.assertIn("Sentence two", chunks[1].text)
        self.assertIn("pressure on the chunk size", chunks[1].text)
        self.assertTrue(chunks[1].text.endswith("chunk size"))
        self.assertIn("Sentence three", chunks[2].text)
        self.assertIn("Sentence four", chunks[-1].text)


if __name__ == "__main__":
    unittest.main()
