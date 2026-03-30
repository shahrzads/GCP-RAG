import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gcp_rag_demo.models import DocumentChunk
from gcp_rag_demo.models import IndexEntry
from gcp_rag_demo.retrieval import VertexAIVectorSearchRetriever
from gcp_rag_demo.retrieval import build_chunk_store


class _FakeDatapoint:
    def __init__(self, datapoint_id):
        self.datapoint_id = datapoint_id


class _FakeNeighbor:
    def __init__(self, datapoint_id, distance, direct_id=None):
        self.datapoint = _FakeDatapoint(datapoint_id)
        self.distance = distance
        self.id = direct_id


class _FakeEndpoint:
    def __init__(self, deployed_indexes=None):
        self.deployed_indexes = deployed_indexes or []

    def find_neighbors(self, deployed_index_id, queries, num_neighbors):
        self.deployed_index_id = deployed_index_id
        self.queries = queries
        self.num_neighbors = num_neighbors
        return [[_FakeNeighbor("chunk-a", -0.95), _FakeNeighbor("chunk-b", -0.10)]]

    @classmethod
    def create(cls, display_name, network, public_endpoint_enabled):
        endpoint = cls()
        endpoint.display_name = display_name
        endpoint.network = network
        endpoint.public_endpoint_enabled = public_endpoint_enabled
        endpoint.resource_name = "projects/demo/locations/us-central1/indexEndpoints/123"
        return endpoint

    def deploy_index(self, index, deployed_index_id):
        self.deployed_indexes.append(type("DeployedIndex", (), {"deployed_index_id": deployed_index_id})())


class _FakeIndex:
    def __init__(self, resource_name, update_method="STREAM_UPDATE"):
        self.resource_name = resource_name
        self._gca_resource = type("GcaResource", (), {"index_update_method": update_method})()
        self.upserted = []
        self.removed = []
        self.updated = []

    def upsert_datapoints(self, datapoints):
        self.upserted.extend(datapoints)

    def remove_datapoints(self, datapoint_ids):
        self.removed.extend(datapoint_ids)

    def update_embeddings(self, contents_delta_uri, is_complete_overwrite):
        self.updated.append((contents_delta_uri, is_complete_overwrite))


class _FakeMatchingEngineIndexFactory:
    def __init__(self, existing_index=None):
        self.existing_index = existing_index
        self.created_index = None

    def __call__(self, index_name):
        self.requested_index_name = index_name
        return self.existing_index

    def create_tree_ah_index(self, **kwargs):
        self.create_kwargs = kwargs
        self.created_index = _FakeIndex("projects/demo/locations/us-central1/indexes/123", kwargs["index_update_method"])
        return self.created_index


class _FakeSdk:
    def __init__(self, existing_index=None, endpoint=None):
        self.index_factory = _FakeMatchingEngineIndexFactory(existing_index=existing_index)
        self.endpoint_instance = endpoint or _FakeEndpoint()
        self.MatchingEngineIndex = self.index_factory
        self.MatchingEngineIndexEndpoint = self._EndpointFactory(self.endpoint_instance)

    def init(self, project, location):
        self.project = project
        self.location = location

    class _EndpointFactory:
        def __init__(self, endpoint):
            self.endpoint = endpoint

        def __call__(self, index_endpoint_name):
            self.endpoint.resource_name = index_endpoint_name
            return self.endpoint

        def create(self, display_name, network, public_endpoint_enabled):
            endpoint = _FakeEndpoint.create(
                display_name=display_name,
                network=network,
                public_endpoint_enabled=public_endpoint_enabled,
            )
            self.endpoint = endpoint
            return endpoint


class _FakeDistanceMeasureType:
    DOT_PRODUCT_DISTANCE = "DOT_PRODUCT_DISTANCE"


class _FakeFeatureNormType:
    UNIT_L2_NORM = "UNIT_L2_NORM"


class _FakeIndexConfigModule:
    DistanceMeasureType = _FakeDistanceMeasureType
    FeatureNormType = _FakeFeatureNormType


class RetrievalTests(unittest.TestCase):
    def test_retrieve_uses_vector_search_neighbors_and_chunk_store(self):
        entries = [
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-a",
                    doc_id="doc-a",
                    title="Cloud Storage",
                    category="storage",
                    text="Cloud Storage holds source files.",
                    source_uri="kb://storage",
                    chunk_index=0,
                ),
                embedding=[1.0, 0.0],
            ),
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-b",
                    doc_id="doc-b",
                    title="Vector Search",
                    category="search",
                    text="Vector Search handles large retrieval workloads.",
                    source_uri="kb://vector-search",
                    chunk_index=0,
                ),
                embedding=[0.0, 1.0],
            ),
        ]

        endpoint = _FakeEndpoint()
        retriever = VertexAIVectorSearchRetriever(
            project_id="demo-project",
            location="us-central1",
            index_endpoint=endpoint,
        )

        results = retriever.retrieve(
            [0.95, 0.05],
            chunk_store=build_chunk_store(entries),
            deployed_index_id="rag_demo_index",
            top_k=2,
        )

        self.assertEqual(endpoint.deployed_index_id, "rag_demo_index")
        self.assertEqual(endpoint.num_neighbors, 2)
        self.assertEqual(results[0].chunk_id, "chunk-a")
        self.assertGreater(results[0].score, results[1].score)

    def test_retrieve_accepts_neighbor_direct_id(self):
        entries = [
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-a",
                    doc_id="doc-a",
                    title="Cloud Storage",
                    category="storage",
                    text="Cloud Storage holds source files.",
                    source_uri="kb://storage",
                    chunk_index=0,
                ),
                embedding=[1.0, 0.0],
            )
        ]

        endpoint = _FakeEndpoint()
        endpoint.find_neighbors = lambda deployed_index_id, queries, num_neighbors: [[_FakeNeighbor("ignored", -0.95, "chunk-a")]]
        retriever = VertexAIVectorSearchRetriever(
            project_id="demo-project",
            location="us-central1",
            index_endpoint=endpoint,
        )

        results = retriever.retrieve(
            [0.95, 0.05],
            chunk_store=build_chunk_store(entries),
            deployed_index_id="rag_demo_index",
            top_k=1,
        )

        self.assertEqual(results[0].chunk_id, "chunk-a")

    def test_ensure_index_ready_uses_stream_upserts_and_removes_stale_datapoints(self):
        existing_index = _FakeIndex("projects/demo/locations/us-central1/indexes/123", update_method="STREAM_UPDATE")
        endpoint = _FakeEndpoint(deployed_indexes=[type("DeployedIndex", (), {"deployed_index_id": "rag_demo_index"})()])
        sdk = _FakeSdk(existing_index=existing_index, endpoint=endpoint)
        retriever = VertexAIVectorSearchRetriever(
            project_id="demo-project",
            location="us-central1",
            index_endpoint_name="projects/demo/locations/us-central1/indexEndpoints/123",
            sdk_module=sdk,
            index_config_module=_FakeIndexConfigModule,
        )

        entries = [
            IndexEntry(
                chunk=DocumentChunk(
                    chunk_id="chunk-a",
                    doc_id="doc-a",
                    title="Cloud Storage",
                    category="storage",
                    text="Cloud Storage holds source files.",
                    source_uri="kb://storage",
                    chunk_index=0,
                ),
                embedding=[1.0, 0.0],
            )
        ]

        retriever.ensure_index_ready(
            contents_delta_uri="gs://bucket/vector-search",
            dimensions=2,
            index_name="projects/demo/locations/us-central1/indexes/123",
            index_display_name="demo-index",
            index_endpoint_name="projects/demo/locations/us-central1/indexEndpoints/123",
            index_endpoint_display_name="demo-endpoint",
            deployed_index_id="rag_demo_index",
            index_update_method="STREAM_UPDATE",
            entries=entries,
            previous_chunk_ids=["chunk-a", "chunk-b"],
            approximate_neighbors_count=10,
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=10,
        )

        self.assertEqual(existing_index.upserted[0].datapoint_id, "chunk-a")
        self.assertEqual(existing_index.removed, ["chunk-b"])
        self.assertEqual(existing_index.updated, [])

    def test_ensure_index_ready_creates_stream_update_index_when_missing(self):
        sdk = _FakeSdk(existing_index=None, endpoint=_FakeEndpoint())
        retriever = VertexAIVectorSearchRetriever(
            project_id="demo-project",
            location="us-central1",
            sdk_module=sdk,
            index_config_module=_FakeIndexConfigModule,
        )

        retriever.ensure_index_ready(
            contents_delta_uri="gs://bucket/vector-search",
            dimensions=2,
            index_name=None,
            index_display_name="demo-index",
            index_endpoint_name=None,
            index_endpoint_display_name="demo-endpoint",
            deployed_index_id="rag_demo_index",
            index_update_method="STREAM_UPDATE",
            entries=[],
            previous_chunk_ids=[],
            approximate_neighbors_count=10,
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=10,
        )

        self.assertEqual(sdk.index_factory.create_kwargs["index_update_method"], "STREAM_UPDATE")


if __name__ == "__main__":
    unittest.main()
