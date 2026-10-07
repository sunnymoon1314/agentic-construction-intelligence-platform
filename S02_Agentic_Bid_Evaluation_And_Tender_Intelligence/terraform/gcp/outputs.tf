output "cloud_run_service_url" {
  description = "Public URL of the S02 Tender Evaluation Cloud Run Service"
  value       = google_cloud_run_v2_service.tender_engine_service.uri
}

output "medallion_bucket_name" {
  description = "Name of the GCS bucket storing the Medallion Data Lake"
  value       = google_storage_bucket.tender_data_lake.name
}

output "artifact_registry_repo" {
  description = "Artifact Registry Docker repository path"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.tender_repo.repository_id}"
}
