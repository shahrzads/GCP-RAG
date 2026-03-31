locals {
  project_services = toset([
    "aiplatform.googleapis.com",
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ])

  common_labels = merge(
    {
      app          = "gcp-rag-demo"
      "managed-by" = "terraform"
    },
    var.labels,
  )

  github_repository = "${var.github_owner}/${var.github_repository}"

  artifact_registry_hostname = "${var.region}-docker.pkg.dev"

  artifact_registry_path = format(
    "%s/%s/%s",
    local.artifact_registry_hostname,
    var.project_id,
    google_artifact_registry_repository.app.repository_id,
  )

  app_env_vars = merge(
    {
      GCP_PROJECT_ID                             = var.project_id
      GCP_LOCATION                               = var.region
      GCS_BUCKET_NAME                            = google_storage_bucket.artifacts.name
      EMBEDDING_MODEL                            = var.embedding_model
      EMBEDDING_DIMENSION                        = tostring(var.embedding_dimension)
      GENERATION_MODEL                           = var.generation_model
      GENERATION_TEMPERATURE                     = tostring(var.generation_temperature)
      GENERATION_MAX_OUTPUT_TOKENS               = tostring(var.generation_max_output_tokens)
      VECTOR_SEARCH_INDEX_NAME                   = var.vector_search_index_name
      VECTOR_SEARCH_INDEX_DISPLAY_NAME           = var.vector_search_index_display_name
      VECTOR_SEARCH_INDEX_ENDPOINT_NAME          = var.vector_search_index_endpoint_name
      VECTOR_SEARCH_INDEX_ENDPOINT_DISPLAY_NAME  = var.vector_search_index_endpoint_display_name
      VECTOR_SEARCH_DEPLOYED_INDEX_ID            = var.vector_search_deployed_index_id
      VECTOR_SEARCH_INDEX_UPDATE_METHOD          = var.vector_search_index_update_method
      VECTOR_SEARCH_ARTIFACT_PREFIX              = var.vector_search_artifact_prefix
      VECTOR_SEARCH_APPROXIMATE_NEIGHBORS_COUNT  = tostring(var.vector_search_approximate_neighbors_count)
      VECTOR_SEARCH_LEAF_NODE_EMBEDDING_COUNT    = tostring(var.vector_search_leaf_node_embedding_count)
      VECTOR_SEARCH_LEAF_NODES_TO_SEARCH_PERCENT = tostring(var.vector_search_leaf_nodes_to_search_percent)
      VECTOR_SEARCH_NETWORK                      = var.vector_search_network
      INDEX_ARTIFACT_BLOB                        = var.index_artifact_blob
      CHUNK_PREVIEW_BLOB                         = var.chunk_preview_blob
      SOURCE_ARTIFACT_PREFIX                     = var.source_artifact_prefix
      CHUNK_SIZE                                 = tostring(var.chunk_size)
      CHUNK_OVERLAP                              = tostring(var.chunk_overlap)
    },
    var.extra_env_vars,
  )
}

resource "google_project_service" "required" {
  for_each = local.project_services

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "artifacts" {
  name                        = var.bucket_name
  location                    = var.bucket_location
  project                     = var.project_id
  labels                      = local.common_labels
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository" "app" {
  project       = var.project_id
  location      = var.region
  repository_id = var.artifact_registry_repository
  format        = "DOCKER"
  labels        = local.common_labels

  depends_on = [google_project_service.required]
}

resource "google_service_account" "runtime" {
  project      = var.project_id
  account_id   = var.runtime_service_account_id
  display_name = "GCP RAG runtime"
}

resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = var.deploy_service_account_id
  display_name = "GCP RAG deployer"
}

resource "google_project_iam_member" "runtime_project_roles" {
  for_each = toset([
    "roles/aiplatform.admin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "runtime_bucket_access" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "deployer_project_roles" {
  for_each = toset([
    "roles/artifactregistry.writer",
    "roles/run.admin",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_runtime_impersonation" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = var.workload_identity_pool_id
  display_name              = "GitHub Actions"
  description               = "Federated identity pool for GitHub Actions deployments."
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = var.workload_identity_provider_id
  display_name                       = "GitHub Actions provider"
  description                        = "OIDC provider for ${local.github_repository}."
  attribute_condition                = "assertion.repository == '${local.github_repository}'"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.aud"              = "assertion.aud"
    "attribute.ref"              = "assertion.ref"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github_deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${local.github_repository}"
}

resource "google_cloud_run_v2_service" "app" {
  name                = var.cloud_run_service_name
  project             = var.project_id
  location            = var.region
  ingress             = var.cloud_run_ingress
  deletion_protection = false
  labels              = local.common_labels

  template {
    service_account = google_service_account.runtime.email
    timeout         = format("%ss", var.cloud_run_timeout_seconds)

    scaling {
      min_instance_count = var.cloud_run_min_instances
      max_instance_count = var.cloud_run_max_instances
    }

    containers {
      image = var.cloud_run_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = var.cloud_run_cpu
          memory = var.cloud_run_memory
        }
      }

      dynamic "env" {
        for_each = local.app_env_vars
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  depends_on = [
    google_project_service.required,
    google_storage_bucket_iam_member.runtime_bucket_access,
    google_project_iam_member.runtime_project_roles,
  ]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  count = var.allow_unauthenticated ? 1 : 0

  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
