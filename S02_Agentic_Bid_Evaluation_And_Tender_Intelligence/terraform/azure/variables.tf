variable "location" {
  description = "Azure region"
  type        = string
  default     = "southeastasia"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "docker_image" {
  description = "The Docker image for the container app. Defaults to a placeholder until you push your real image."
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}
