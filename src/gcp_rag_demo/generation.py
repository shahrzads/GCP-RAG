"""Answer generation helpers for grounded RAG responses on Vertex AI."""

from typing import Sequence

from gcp_rag_demo.models import RetrievalResult


def build_context_block(results: Sequence[RetrievalResult]) -> str:
    """Serialize retrieved chunks into a prompt-ready context block."""
    if not results:
        return "No retrieved context was available."

    sections = []
    for index, result in enumerate(results, start=1):
        sections.append(
            "\n".join(
                [
                    "Source {0}".format(index),
                    "chunk_id: {0}".format(result.chunk_id),
                    "title: {0}".format(result.title),
                    "source_uri: {0}".format(result.source_uri),
                    "score: {0:.4f}".format(result.score),
                    "text: {0}".format(result.text),
                ]
            )
        )
    return "\n\n".join(sections)


def build_rag_prompt(question: str, results: Sequence[RetrievalResult]) -> str:
    """Build the grounded prompt sent to the answer-generation model."""
    return (
        "You are a helpful RAG assistant for a Google Cloud demo.\n"
        "Answer the user's question using only the retrieved context below.\n"
        "If the context does not contain enough information, say so clearly.\n"
        "Cite supporting chunk IDs inline in square brackets, for example [doc-001-chunk-00].\n"
        "Keep the answer concise and factual.\n\n"
        "Question:\n"
        "{0}\n\n"
        "Retrieved context:\n"
        "{1}\n\n"
        "Return:\n"
        "1. A short answer grounded in the context.\n"
        "2. A final line starting with 'Sources:' followed by the chunk IDs you used."
    ).format(question.strip(), build_context_block(results))


class VertexAIAnswerGenerator:
    """Generate grounded answers from retrieved chunks with Gemini on Vertex AI."""

    def __init__(
        self,
        project_id: str,
        location: str,
        model_name: str,
        temperature: float = 0.2,
        max_output_tokens: int = 512,
    ) -> None:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - depends on external package
            raise RuntimeError(
                "google-genai is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
            ) from exc

        self._client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
            http_options=types.HttpOptions(api_version="v1"),
        )
        self._model_name = model_name
        self._config = types.GenerateContentConfig(
            temperature=temperature,
            candidate_count=1,
            max_output_tokens=max_output_tokens,
        )

    def generate_answer(self, question: str, results: Sequence[RetrievalResult]) -> str:
        """Generate a grounded answer for the user question."""
        response = self._client.models.generate_content(
            model=self._model_name,
            contents=build_rag_prompt(question, results),
            config=self._config,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Vertex AI returned an empty answer.")
        return text

    def close(self) -> None:
        """Close the underlying SDK client."""
        self._client.close()
