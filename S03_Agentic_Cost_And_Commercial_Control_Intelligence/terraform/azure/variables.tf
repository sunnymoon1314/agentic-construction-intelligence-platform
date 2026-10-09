variable "azure_location" {
  description = "Azure region for deployment"
  type        = string
  default     = "southeastasia"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "app_port" {
  description = "Application port for container ingress"
  type        = number
  default     = 8086
}

variable "docker_image" {
  description = "Initial container image for bootstrap"
  type        = string
  default     = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
}
