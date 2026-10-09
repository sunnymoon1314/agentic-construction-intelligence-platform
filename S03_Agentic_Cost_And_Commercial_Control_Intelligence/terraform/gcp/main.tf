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
resource "google_storage_bucket" "commercial_lake" {
  name          = "acip-s03-commercial-lake-${var.project_id}"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "commercial_repo" {
  location      = var.region
  repository_id = "acip-s03-repo"
  description   = "Docker repository for ACIP S03 Commercial Control Engine"
  format        = "DOCKER"
}

# 3. Google Cloud Run v2 Service
resource "google_cloud_run_v2_service" "commercial_service" {
  name     = "acip-s03-commercial-cockpit"
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
        name  = "COMMERCIAL_LAKE_BUCKET"
        value = "gs://${google_storage_bucket.commercial_lake.name}"
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
  location = google_cloud_run_v2_service.commercial_service.location
  name     = google_cloud_run_v2_service.commercial_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
