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

# 1. Medallion Analytical Data Lake (Cloud Storage)
resource "google_storage_bucket" "tender_data_lake" {
  name                     = "${var.project_id}-s02-tender-lake-${var.environment}"
  location                 = var.region
  force_destroy            = true
  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 90
    }
  }
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "tender_repo" {
  location      = var.region
  repository_id = "acip-s02-tender-engine"
  description   = "Docker repository for S02 Tender Evaluation FastMCP Engine"
  format        = "DOCKER"
}

# 3. Cloud Run Service (S02 Analytical Engine & FastMCP Server)
resource "google_cloud_run_v2_service" "tender_engine_service" {
  name     = "acip-s02-tender-engine-${var.environment}"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    containers {
      image = var.docker_image
      ports {
        container_port = 8085
      }
      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "CLOUD_PROVIDER"
        value = "GCP"
      }
      env {
        name  = "GCS_MEDALLION_BUCKET"
        value = google_storage_bucket.tender_data_lake.name
      }
    }
  }
}

# 4. IAM - Allow unauthenticated or committee invocations
resource "google_cloud_run_v2_service_iam_member" "invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.tender_engine_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
