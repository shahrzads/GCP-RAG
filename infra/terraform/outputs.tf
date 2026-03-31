output "artifact_bucket_name" {
  description = "Cloud Storage bucket used by the application."
  value       = google_storage_bucket.artifacts.name
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name."
  value       = google_artifact_registry_repository.app.repository_id
}

output "artifact_registry_image_base" {
  description = "Base image path for pushes from CI/CD."
  value       = local.artifact_registry_path
}

output "cloud_run_service_name" {
  description = "Cloud Run service name."
  value       = google_cloud_run_v2_service.app.name
}

output "cloud_run_service_url" {
  description = "Cloud Run service URL."
  value       = google_cloud_run_v2_service.app.uri
}

output "github_workload_identity_provider" {
  description = "Workload Identity Provider resource name for GitHub Actions."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "github_deploy_service_account_email" {
  description = "Service account email used by GitHub Actions for deployments."
  value       = google_service_account.deployer.email
}

output "runtime_service_account_email" {
  description = "Service account email used by the Cloud Run service."
  value       = google_service_account.runtime.email
}
