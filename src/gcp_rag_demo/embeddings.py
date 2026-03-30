"""Embedding client wrappers for Vertex AI text embeddings."""

from typing import Iterable
from typing import List
from typing import Optional

from gcp_rag_demo.models import DocumentChunk


class VertexAIEmbeddingClient:
    """Thin wrapper around the Vertex AI text embedding model."""

    def __init__(
        self,
        project_id: str,
        location: str,
        model_name: str,
        output_dimensionality: Optional[int] = None,
    ) -> None:
        try:
            import vertexai
            from vertexai.language_models import TextEmbeddingInput
            from vertexai.language_models import TextEmbeddingModel
        except ImportError as exc:  # pragma: no cover - depends on external package
            raise RuntimeError(
                "Vertex AI SDK is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
            ) from exc

        vertexai.init(project=project_id, location=location)
        self._input_type = TextEmbeddingInput
        self._model = TextEmbeddingModel.from_pretrained(model_name)
        self.output_dimensionality = output_dimensionality

    def _embed_texts(
        self,
        texts: Iterable[str],
        task_type: str,
        titles: Optional[Iterable[Optional[str]]] = None,
    ) -> List[List[float]]:
        """Embed one or more texts for the requested Vertex AI task type."""
        results = []
        title_list = list(titles) if titles is not None else []

        for index, text in enumerate(texts):
            title = title_list[index] if title_list else None
            embedding_input = self._input_type(text=text, task_type=task_type, title=title)
            kwargs = {}
            if self.output_dimensionality:
                kwargs["output_dimensionality"] = self.output_dimensionality
            response = self._model.get_embeddings([embedding_input], **kwargs)
            results.append(list(response[0].values))
        return results

    def embed_documents(self, chunks: Iterable[DocumentChunk]) -> List[List[float]]:
        """Embed document chunks for retrieval indexing."""
        chunk_list = list(chunks)
        texts = [chunk.text for chunk in chunk_list]
        titles = [chunk.title for chunk in chunk_list]
        return self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT", titles=titles)

    def embed_query(self, question: str) -> List[float]:
        """Embed a user question for retrieval search."""
        return self._embed_texts([question], task_type="RETRIEVAL_QUERY")[0]
