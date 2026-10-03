# Google Cloud Run Provisioning for Enterprise MCP Server

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required APIs (Optional, but good practice)
resource "google_project_service" "artifact_registry_api" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run_api" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "vertex_ai_api" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

# 2. Artifact Registry Repository
resource "google_artifact_registry_repository" "agent_repo" {
  location      = var.region
  repository_id = var.project_name
  description   = "Docker repository for the Enterprise MCP Agent"
  format        = "DOCKER"
  depends_on    = [google_project_service.artifact_registry_api]
}

# 3. Service Account for Cloud Run (Least Privilege)
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.project_name}-sa"
  display_name = "Service Account for Enterprise MCP Cloud Run"
}

resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# 4. Cloud Run Service
resource "google_cloud_run_v2_service" "mcp_server" {
  name     = var.project_name
  location = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.cloud_run_sa.email
    
    containers {
      image = var.docker_image
      
      ports {
        container_port = 8000
      }
      
      env {
        name  = "CLOUD_PROVIDER"
        value = "GCP"
      }
    }
  }

  depends_on = [google_project_service.cloud_run_api]
}

# 5. Allow Unauthenticated Access (Public Web UI)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.mcp_server.project
  location = google_cloud_run_v2_service.mcp_server.location
  name     = google_cloud_run_v2_service.mcp_server.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
