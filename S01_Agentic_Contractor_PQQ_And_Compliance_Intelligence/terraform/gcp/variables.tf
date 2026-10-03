variable "project_id" {
  description = "The GCP Project ID"
  type        = string
}

variable "region" {
  description = "The GCP Region"
  type        = string
  default     = "us-central1"
}

variable "project_name" {
  description = "The name of the project"
  type        = string
  default     = "enterprise-mcp-agent"
}

variable "docker_image" {
  description = "The Docker image for the MCP server. Defaults to a placeholder until you push your real image."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}
