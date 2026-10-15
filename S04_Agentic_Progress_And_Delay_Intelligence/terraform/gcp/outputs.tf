output "artifact_registry_url" {
  description = "The URL of the Artifact Registry repository to push your Docker image to"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.delay_repo.repository_id}"
}

output "cloud_run_url" {
  description = "The public URL of the deployed ACIP S04 Cloud Run service"
  value       = google_cloud_run_v2_service.delay_service.uri
}

output "delay_lake_bucket" {
  description = "GCS bucket storing Approach 3 Parquet lakehouse"
  value       = google_storage_bucket.delay_lake.name
}

output "project_id" {
  description = "The GCP Project ID"
  value       = var.project_id
}
