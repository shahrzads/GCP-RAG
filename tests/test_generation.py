import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcp_rag_demo.generation import build_context_block
from gcp_rag_demo.generation import build_rag_prompt
from gcp_rag_demo.models import RetrievalResult


class GenerationPromptTests(unittest.TestCase):
    def test_build_context_block_includes_chunk_metadata(self):
        results = [
            RetrievalResult(
                chunk_id="doc-1-chunk-00",
                doc_id="doc-1",
                title="Cloud Storage",
                source_uri="kb://storage",
                score=0.9123,
                text="Cloud Storage stores source and artifact files.",
            )
        ]

        context = build_context_block(results)

        self.assertIn("chunk_id: doc-1-chunk-00", context)
        self.assertIn("title: Cloud Storage", context)
        self.assertIn("source_uri: kb://storage", context)
        self.assertIn("Cloud Storage stores source and artifact files.", context)

    def test_build_rag_prompt_references_question_and_citation_rules(self):
        results = [
            RetrievalResult(
                chunk_id="doc-1-chunk-00",
                doc_id="doc-1",
                title="Vertex AI",
                source_uri="kb://vertex-ai",
                score=0.9912,
                text="Vertex AI creates embeddings and can generate grounded answers.",
            )
        ]

        prompt = build_rag_prompt("How is Vertex AI used here?", results)

        self.assertIn("How is Vertex AI used here?", prompt)
        self.assertIn("[doc-001-chunk-00]", prompt)
        self.assertIn("Sources:", prompt)
        self.assertIn("doc-1-chunk-00", prompt)


if __name__ == "__main__":
    unittest.main()
