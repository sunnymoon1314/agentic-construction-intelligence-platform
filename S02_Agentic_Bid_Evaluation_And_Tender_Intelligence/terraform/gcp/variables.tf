variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy resources into"
  type        = string
  default     = "asia-southeast1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "docker_image" {
  description = "The Docker image for the Cloud Run service. Defaults to a public hello image until you push your real image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
