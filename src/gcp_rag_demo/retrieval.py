"""Helpers for syncing and querying Vertex AI Vector Search."""

from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

from google.api_core.exceptions import AlreadyExists

from gcp_rag_demo.models import IndexEntry
from gcp_rag_demo.models import RetrievalResult


def build_chunk_store(entries: Sequence[IndexEntry]) -> Dict[str, IndexEntry]:
    """Build a chunk lookup table keyed by chunk ID."""
    return {entry.chunk.chunk_id: entry for entry in entries}


class VertexAIVectorSearchRetriever:
    """Manage Vertex AI Vector Search indexing and retrieval."""

    def __init__(
        self,
        project_id: str,
        location: str,
        index_endpoint_name: Optional[str] = None,
        sdk_module=None,
        index_config_module=None,
        index_endpoint=None,
    ) -> None:
        self._sdk = sdk_module
        self._index_config = index_config_module
        self._project_id = project_id
        self._location = location
        self._index_endpoint_name = index_endpoint_name
        self._endpoint = index_endpoint

    def _load_sdk(self) -> None:
        """Import the Vertex AI SDK on demand."""
        if self._sdk is not None and self._index_config is not None:
            return

        try:
            from google.cloud import aiplatform
            from google.cloud.aiplatform.matching_engine import matching_engine_index_config
        except ImportError as exc:  # pragma: no cover - depends on external package
            raise RuntimeError(
                "google-cloud-aiplatform is not installed. Run `pip install -e .` inside a Python 3.11+ virtual environment."
            ) from exc

        self._sdk = aiplatform
        self._index_config = matching_engine_index_config

    def _init_sdk(self) -> None:
        """Initialize the Vertex AI SDK with the configured project and location."""
        self._load_sdk()
        self._sdk.init(project=self._project_id, location=self._location)

    def _get_endpoint(self):
        """Return the configured Vector Search endpoint resource."""
        if self._endpoint is not None:
            return self._endpoint
        if not self._index_endpoint_name:
            raise RuntimeError("Vector Search endpoint is not configured.")

        self._init_sdk()
        self._endpoint = self._sdk.MatchingEngineIndexEndpoint(
            index_endpoint_name=self._index_endpoint_name
        )
        return self._endpoint

    @staticmethod
    def _normalize_index_update_method(index_update_method: str) -> str:
        """Return the normalized Vertex AI index update method."""
        normalized = (index_update_method or "BATCH_UPDATE").strip().upper()
        if normalized not in {"STREAM_UPDATE", "BATCH_UPDATE"}:
            raise RuntimeError("VECTOR_SEARCH_INDEX_UPDATE_METHOD must be STREAM_UPDATE or BATCH_UPDATE.")
        return normalized

    @staticmethod
    def _current_index_update_method(index) -> str:
        """Read the current update method from an existing Vertex AI index resource."""
        gca_resource = getattr(index, "_gca_resource", None)
        method = getattr(gca_resource, "index_update_method", None)
        if hasattr(method, "name"):
            return str(method.name).upper()
        if method is None:
            return "BATCH_UPDATE"
        return str(method).upper()

    def _build_datapoints(self, entries: Sequence[IndexEntry]):
        """Convert index entries into Vertex AI datapoints for streaming updates."""
        from google.cloud.aiplatform_v1.types.index import IndexDatapoint

        return [
            IndexDatapoint(
                datapoint_id=entry.chunk.chunk_id,
                feature_vector=entry.embedding,
            )
            for entry in entries
        ]

    def ensure_index_ready(
        self,
        contents_delta_uri: str,
        dimensions: int,
        index_name: Optional[str],
        index_display_name: str,
        index_endpoint_name: Optional[str],
        index_endpoint_display_name: str,
        deployed_index_id: str,
        index_update_method: str,
        entries: Sequence[IndexEntry],
        previous_chunk_ids: Sequence[str],
        approximate_neighbors_count: int,
        leaf_node_embedding_count: int,
        leaf_nodes_to_search_percent: int,
        network: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Create or update the Vector Search index and ensure it is deployed."""
        self._init_sdk()
        self._index_endpoint_name = index_endpoint_name or self._index_endpoint_name
        normalized_update_method = self._normalize_index_update_method(index_update_method)

        if index_name:
            index = self._sdk.MatchingEngineIndex(index_name=index_name)
            current_update_method = self._current_index_update_method(index)
            if current_update_method != normalized_update_method:
                raise RuntimeError(
                    "Existing Vector Search index uses {0}, but the app is configured for {1}. "
                    "Create a fresh index or align VECTOR_SEARCH_INDEX_UPDATE_METHOD.".format(
                        current_update_method,
                        normalized_update_method,
                    )
                )
            if normalized_update_method == "STREAM_UPDATE":
                current_ids = {entry.chunk.chunk_id for entry in entries}
                stale_ids = [chunk_id for chunk_id in previous_chunk_ids if chunk_id not in current_ids]
                index.upsert_datapoints(datapoints=self._build_datapoints(entries))
                if stale_ids:
                    index.remove_datapoints(datapoint_ids=stale_ids)
            else:
                index.update_embeddings(contents_delta_uri=contents_delta_uri, is_complete_overwrite=True)
        else:
            index = self._sdk.MatchingEngineIndex.create_tree_ah_index(
                display_name=index_display_name,
                contents_delta_uri=contents_delta_uri,
                dimensions=dimensions,
                approximate_neighbors_count=approximate_neighbors_count,
                leaf_node_embedding_count=leaf_node_embedding_count,
                leaf_nodes_to_search_percent=leaf_nodes_to_search_percent,
                distance_measure_type=self._index_config.DistanceMeasureType.DOT_PRODUCT_DISTANCE,
                feature_norm_type=self._index_config.FeatureNormType.UNIT_L2_NORM,
                index_update_method=normalized_update_method,
            )

        if self._index_endpoint_name:
            endpoint = self._sdk.MatchingEngineIndexEndpoint(
                index_endpoint_name=self._index_endpoint_name
            )
        else:
            endpoint = self._sdk.MatchingEngineIndexEndpoint.create(
                display_name=index_endpoint_display_name,
                network=network,
                public_endpoint_enabled=True,
            )
            self._index_endpoint_name = endpoint.resource_name

        deployed_index_ids = {
            self._read_deployed_index_id(reference) for reference in endpoint.deployed_indexes
        }
        if deployed_index_id not in deployed_index_ids:
            try:
                endpoint.deploy_index(index=index, deployed_index_id=deployed_index_id)
            except AlreadyExists:
                pass

        self._endpoint = endpoint
        return index.resource_name, endpoint.resource_name

    @staticmethod
    def _read_deployed_index_id(reference) -> Optional[str]:
        """Extract a deployed index ID from SDK resource variants."""
        return getattr(reference, "deployed_index_id", None) or getattr(reference, "id", None)

    @staticmethod
    def _neighbor_id(neighbor) -> Optional[str]:
        """Return the datapoint ID for a neighbor match."""
        direct_id = getattr(neighbor, "id", None)
        if direct_id:
            return direct_id
        datapoint = getattr(neighbor, "datapoint", None)
        return getattr(datapoint, "datapoint_id", None)

    @staticmethod
    def _neighbor_score(neighbor) -> float:
        """Convert Vertex AI distance output into a similarity-like score."""
        return -float(getattr(neighbor, "distance", 0.0))

    def retrieve(
        self,
        query_embedding: List[float],
        chunk_store: Dict[str, IndexEntry],
        deployed_index_id: str,
        top_k: int = 3,
    ) -> List[RetrievalResult]:
        """Query the deployed Vector Search index and map matches back to chunks."""
        endpoint = self._get_endpoint()
        neighbors_per_query = endpoint.find_neighbors(
            deployed_index_id=deployed_index_id,
            queries=[query_embedding],
            num_neighbors=top_k,
        )

        results = []
        for neighbor in neighbors_per_query[0]:
            chunk_id = self._neighbor_id(neighbor)
            if not chunk_id or chunk_id not in chunk_store:
                continue
            entry = chunk_store[chunk_id]
            results.append(
                RetrievalResult(
                    chunk_id=entry.chunk.chunk_id,
                    doc_id=entry.chunk.doc_id,
                    title=entry.chunk.title,
                    source_uri=entry.chunk.source_uri,
                    score=self._neighbor_score(neighbor),
                    text=entry.chunk.text,
                )
            )
        return results
