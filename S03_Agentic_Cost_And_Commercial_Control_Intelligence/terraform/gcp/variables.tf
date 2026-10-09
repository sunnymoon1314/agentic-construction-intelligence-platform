variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for deployment"
  type        = string
  default     = "asia-southeast1"
}

variable "app_port" {
  description = "Port exposed by Cloud Run service"
  type        = number
  default     = 8086
}

variable "docker_image" {
  description = "The initial Docker image for bootstrap before real image push"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
