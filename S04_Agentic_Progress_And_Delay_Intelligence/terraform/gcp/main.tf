terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. GCS Bucket for Approach 3 Parquet Lakehouse
resource "google_storage_bucket" "delay_lake" {
  name          = "acip-s04-delay-lake-${var.project_id}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "delay_repo" {
  location      = var.region
  repository_id = "acip-s04-repo"
  description   = "Docker repository for ACIP S04 Delay Intelligence Engine"
  format        = "DOCKER"
}

# 3. Google Cloud Run v2 Service
resource "google_cloud_run_v2_service" "delay_service" {
  name     = "acip-s04-delay-cockpit"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.docker_image

      ports {
        container_port = var.app_port
      }

      env {
        name  = "CLOUD_PROVIDER"
        value = "GCP"
      }

      env {
        name  = "PROGRESS_DELAY_LAKE_BUCKET"
        value = "gs://${google_storage_bucket.delay_lake.name}"
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }
    }
  }
}

# 4. Allow Unauthenticated Public Ingress
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.delay_service.location
  name     = google_cloud_run_v2_service.delay_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
