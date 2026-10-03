output "artifact_registry_url" {
  description = "The URL of the Artifact Registry repository to push your Docker image to."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.agent_repo.repository_id}"
}

output "cloud_run_url" {
  description = "The public URL of the deployed Enterprise MCP Agent web app."
  value       = google_cloud_run_v2_service.mcp_server.uri
}

output "project_id" {
  description = "The GCP Project ID."
  value       = var.project_id
}
