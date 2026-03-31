variable "project_id" {
  description = "Google Cloud project ID that hosts the demo resources."
  type        = string
}

variable "region" {
  description = "Primary Google Cloud region for Cloud Run, Artifact Registry, and Vertex AI."
  type        = string
  default     = "us-central1"
}

variable "bucket_location" {
  description = "Location for the Cloud Storage bucket that holds source and retrieval artifacts."
  type        = string
  default     = "US-CENTRAL1"
}

variable "bucket_name" {
  description = "Globally unique Cloud Storage bucket name for the demo."
  type        = string
}

variable "artifact_registry_repository" {
  description = "Artifact Registry Docker repository name."
  type        = string
  default     = "gcp-rag-demo"
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name for the Streamlit deployment."
  type        = string
  default     = "gcp-rag-demo"
}

variable "cloud_run_image" {
  description = "Bootstrap image used when Terraform first creates the Cloud Run service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "cloud_run_cpu" {
  description = "CPU limit for the Cloud Run container."
  type        = string
  default     = "1"
}

variable "cloud_run_memory" {
  description = "Memory limit for the Cloud Run container."
  type        = string
  default     = "1Gi"
}

variable "cloud_run_min_instances" {
  description = "Minimum number of Cloud Run instances."
  type        = number
  default     = 0
}

variable "cloud_run_max_instances" {
  description = "Maximum number of Cloud Run instances."
  type        = number
  default     = 2
}

variable "cloud_run_timeout_seconds" {
  description = "Request timeout for Cloud Run."
  type        = number
  default     = 900
}

variable "cloud_run_ingress" {
  description = "Cloud Run ingress policy."
  type        = string
  default     = "INGRESS_TRAFFIC_ALL"
}

variable "allow_unauthenticated" {
  description = "Whether the deployed Streamlit UI should be publicly invokable."
  type        = bool
  default     = true
}

variable "github_owner" {
  description = "GitHub user or organization that owns the repository."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository name that should be allowed to deploy."
  type        = string
}

variable "workload_identity_pool_id" {
  description = "Workload Identity Pool ID for GitHub Actions federation."
  type        = string
  default     = "github-actions"
}

variable "workload_identity_provider_id" {
  description = "Workload Identity Provider ID for GitHub Actions federation."
  type        = string
  default     = "github-provider"
}

variable "runtime_service_account_id" {
  description = "Service account ID used by the Cloud Run service."
  type        = string
  default     = "gcp-rag-runtime"
}

variable "deploy_service_account_id" {
  description = "Service account ID impersonated by GitHub Actions during deployment."
  type        = string
  default     = "gcp-rag-deployer"
}

variable "embedding_model" {
  description = "Vertex AI embedding model."
  type        = string
  default     = "gemini-embedding-001"
}

variable "embedding_dimension" {
  description = "Embedding vector dimensionality."
  type        = number
  default     = 768
}

variable "generation_model" {
  description = "Vertex AI generation model."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "generation_temperature" {
  description = "Temperature used for answer generation."
  type        = number
  default     = 0.0
}

variable "generation_max_output_tokens" {
  description = "Maximum output tokens for answer generation."
  type        = number
  default     = 512
}

variable "vector_search_index_name" {
  description = "Optional existing Vector Search index resource name."
  type        = string
  default     = ""
}

variable "vector_search_index_display_name" {
  description = "Display name for a created Vector Search index."
  type        = string
  default     = "gcp-rag-demo-index"
}

variable "vector_search_index_endpoint_name" {
  description = "Optional existing Vector Search endpoint resource name."
  type        = string
  default     = ""
}

variable "vector_search_index_endpoint_display_name" {
  description = "Display name for a created Vector Search endpoint."
  type        = string
  default     = "gcp-rag-demo-endpoint"
}

variable "vector_search_deployed_index_id" {
  description = "Deployed index ID used by Vector Search."
  type        = string
  default     = "rag_demo_index"
}

variable "vector_search_index_update_method" {
  description = "Vector Search update method."
  type        = string
  default     = "STREAM_UPDATE"
}

variable "vector_search_artifact_prefix" {
  description = "Cloud Storage prefix for Vector Search artifacts."
  type        = string
  default     = "rag-demo/vector-search"
}

variable "vector_search_approximate_neighbors_count" {
  description = "Vector Search approximate neighbors count."
  type        = number
  default     = 10
}

variable "vector_search_leaf_node_embedding_count" {
  description = "Vector Search leaf node embedding count."
  type        = number
  default     = 500
}

variable "vector_search_leaf_nodes_to_search_percent" {
  description = "Vector Search leaf nodes to search percent."
  type        = number
  default     = 10
}

variable "vector_search_network" {
  description = "Optional VPC network for a private Vector Search endpoint."
  type        = string
  default     = ""
}

variable "index_artifact_blob" {
  description = "Cloud Storage blob path for the serialized index artifact."
  type        = string
  default     = "rag-demo/artifacts/index.json"
}

variable "chunk_preview_blob" {
  description = "Cloud Storage blob path for the chunk preview artifact."
  type        = string
  default     = "rag-demo/artifacts/chunks.jsonl"
}

variable "source_artifact_prefix" {
  description = "Cloud Storage prefix for raw uploaded documents."
  type        = string
  default     = "rag-demo/raw"
}

variable "chunk_size" {
  description = "Maximum characters per document chunk."
  type        = number
  default     = 550
}

variable "chunk_overlap" {
  description = "Overlap between document chunks."
  type        = number
  default     = 120
}

variable "extra_env_vars" {
  description = "Additional environment variables injected into Cloud Run."
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Extra labels applied to provisioned resources."
  type        = map(string)
  default     = {}
}
